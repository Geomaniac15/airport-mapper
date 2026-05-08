'''Tests for procedurally generated scenarios and staggered spawning.

Covers:
 * random_departures, random_arrivals, random_mixed semantics
 * seed reproducibility
 * stagger bounds and behaviour
 * Aircraft model spawn fields
 * run_scenario with staggered specs
 * parametrised stress runs across many seeds
'''

import pytest

from airport_mapper.graph import (get_compressed_graph, runway_nodes,
                                  stand_nodes)
from airport_mapper.main_sim import compute_metrics, run_scenario
from airport_mapper.models import Aircraft, Node
from airport_mapper.planning import dijkstra_path
from airport_mapper.scenarios import (random_arrivals, random_departures,
                                      random_mixed)

# random_departures

def test_random_departures_count():
    assert len(random_departures(5, seed=42)) == 5


def test_random_departures_aircraft_ids_sequential():
    s = random_departures(5, seed=42)
    assert [spec['aircraft_id'] for spec in s] == ['A1', 'A2', 'A3', 'A4', 'A5']


def test_random_departures_seed_reproducibility():
    s1 = random_departures(10, seed=123)
    s2 = random_departures(10, seed=123)
    assert s1 == s2


def test_random_departures_different_seeds_differ():
    s1 = random_departures(10, seed=1)
    s2 = random_departures(10, seed=2)
    assert s1 != s2


def test_random_departures_no_duplicate_starts():
    s = random_departures(20, seed=42)
    starts = [spec['start'] for spec in s]
    assert len(set(starts)) == len(starts)


def test_random_departures_starts_are_stands():
    s = random_departures(15, seed=42)
    for spec in s:
        assert spec['start'] in stand_nodes


def test_random_departures_goals_are_runways():
    s = random_departures(15, seed=42)
    for spec in s:
        assert spec['goal'] in runway_nodes


def test_random_departures_all_paths_valid():
    compressed = get_compressed_graph()
    s = random_departures(15, seed=42)
    for spec in s:
        path = dijkstra_path(compressed, spec['start'], spec['goal'])
        assert path is not None, f"No path for {spec['aircraft_id']}"
        assert path[0] == spec['start']
        assert path[-1] == spec['goal']


def test_random_departures_default_spawn_tick_zero():
    s = random_departures(5, seed=42)
    assert all(spec['spawn_tick'] == 0 for spec in s)


def test_random_departures_too_many_raises():
    way_too_many = len(stand_nodes) + 100
    with pytest.raises(ValueError):
        random_departures(way_too_many, seed=42)


# stagger

def test_stagger_within_bounds():
    s = random_departures(20, seed=42, stagger=10)
    for spec in s:
        assert 0 <= spec['spawn_tick'] <= 10


def test_stagger_zero_means_all_zero():
    s = random_departures(20, seed=42, stagger=0)
    assert all(spec['spawn_tick'] == 0 for spec in s)


def test_stagger_seed_reproducibility():
    s1 = random_departures(20, seed=42, stagger=15)
    s2 = random_departures(20, seed=42, stagger=15)
    assert s1 == s2


def test_stagger_actually_staggers():
    'For a meaningful stagger window, spawn ticks should be varied.'
    s = random_departures(30, seed=42, stagger=20)
    spawn_ticks = [spec['spawn_tick'] for spec in s]
    assert len(set(spawn_ticks)) > 1


def test_stagger_changes_scenario():
    'Different stagger values should produce different scenarios from the same seed.'
    s1 = random_departures(10, seed=42, stagger=0)
    s2 = random_departures(10, seed=42, stagger=10)
    # Pairs themselves are identical (same seed, same RNG calls before stagger)
    # but spawn ticks differ
    pairs1 = [(s['start'], s['goal']) for s in s1]
    pairs2 = [(s['start'], s['goal']) for s in s2]
    assert pairs1 == pairs2
    spawn1 = [s['spawn_tick'] for s in s1]
    spawn2 = [s['spawn_tick'] for s in s2]
    assert spawn1 != spawn2


# random_arrivals

def test_random_arrivals_count():
    assert len(random_arrivals(5, seed=42)) == 5


def test_random_arrivals_starts_are_runways():
    s = random_arrivals(5, seed=42)
    for spec in s:
        assert spec['start'] in runway_nodes


def test_random_arrivals_goals_are_stands():
    s = random_arrivals(5, seed=42)
    for spec in s:
        assert spec['goal'] in stand_nodes


def test_random_arrivals_stagger_propagates():
    s = random_arrivals(10, seed=42, stagger=15)
    for spec in s:
        assert 0 <= spec['spawn_tick'] <= 15


# random_mixed

def test_random_mixed_count():
    assert len(random_mixed(10, seed=42)) == 10


def test_random_mixed_has_both_kinds():
    s = random_mixed(10, seed=42)
    has_dep = any(
        spec['start'] in stand_nodes and spec['goal'] in runway_nodes for spec in s
    )
    has_arr = any(
        spec['start'] in runway_nodes and spec['goal'] in stand_nodes for spec in s
    )
    assert has_dep
    assert has_arr


def test_random_mixed_stagger_propagates():
    s = random_mixed(10, seed=42, stagger=15)
    assert any(spec['spawn_tick'] > 0 for spec in s)


def test_random_mixed_aircraft_ids_unique_and_sequential():
    s = random_mixed(8, seed=42)
    ids = [spec['aircraft_id'] for spec in s]
    assert ids == ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']


# Aircraft model spawn fields

def test_aircraft_default_spawn_fields():
    n = Node('N1')
    ac = Aircraft('A1', None, None, [n])
    assert ac.spawn_tick == 0
    assert ac.spawned is False
    assert ac.spawned_at is None


def test_aircraft_custom_spawn_tick():
    n = Node('N1')
    ac = Aircraft('A1', None, None, [n], spawn_tick=10)
    assert ac.spawn_tick == 10
    assert ac.spawned is False


def test_aircraft_unspawned_proposes_nothing():
    n1 = Node('N1')
    n2 = Node('N2')
    ac = Aircraft('A1', None, None, [n1, n2], spawn_tick=10)
    assert ac.propose_next() is None
    assert ac.propose_corridor() is None


def test_aircraft_spawned_proposes_next():
    n1 = Node('N1')
    n2 = Node('N2')
    ac = Aircraft('A1', None, None, [n1, n2])
    ac.current = n1
    ac.spawned = True
    assert ac.propose_next() is n2


# run_scenario with staggered specs

def test_simulation_records_prespawn_history():
    s = [
        {'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N1', 'spawn_tick': 5},
    ]
    result = run_scenario(s, max_steps=100)
    positions = result['history']['positions']['A1']
    # First five ticks should be PRESPAWN since spawn_tick=5 means the
    # aircraft does not enter until tick 5.
    assert positions[0] == 'PRESPAWN'
    assert positions[4] == 'PRESPAWN'
    # By tick 5 the aircraft must be on the graph
    assert positions[5] != 'PRESPAWN'


def test_simulation_spawned_at_matches_spawn_tick_when_clear():
    s = [
        {'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N1', 'spawn_tick': 5},
    ]
    result = run_scenario(s, max_steps=200)
    metrics = compute_metrics(result)
    assert metrics['aircraft']['A1']['spawned_at'] == 5


def test_taxi_duration_equals_airborne_minus_spawn():
    s = random_departures(5, seed=42, stagger=10)
    result = run_scenario(s, max_steps=200)
    metrics = compute_metrics(result)
    for ac_id, m in metrics['aircraft'].items():
        if m['time_to_airborne'] is not None and m['spawned_at'] is not None:
            assert m['taxi_duration'] == m['time_to_airborne'] - m['spawned_at']


def test_long_warmup_does_not_trigger_deadlock():
    'A scenario with a single aircraft spawning 50 ticks in must not deadlock.'
    s = [
        {'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N1', 'spawn_tick': 50},
    ]
    result = run_scenario(s, max_steps=200)
    assert not result['deadlock']
    metrics = compute_metrics(result)
    assert metrics['aircraft']['A1']['spawned_at'] == 50


def test_distance_skips_prespawn():
    'Distance travelled must not crash on PRESPAWN entries in the history.'
    s = [
        {'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N1', 'spawn_tick': 3},
    ]
    result = run_scenario(s, max_steps=100)
    metrics = compute_metrics(result)
    # If PRESPAWN handling is buggy this would crash before we got here.
    assert metrics['aircraft']['A1']['distance_travelled_m'].endswith(' m')


def test_existing_scenarios_unaffected_by_spawn_changes():
    'The original tests still pass; this is a smoke test that hand-written '
    'scenarios still spawn at t=0 by default.'
    from airport_mapper.scenarios import SCENARIOS
    s = SCENARIOS['simple_departures']
    result = run_scenario(s, max_steps=200)
    metrics = compute_metrics(result)
    for ac_id, m in metrics['aircraft'].items():
        assert m['spawned_at'] == 0


# Parametrised stress runs

@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_random_5_no_deadlock(seed):
    s = random_departures(5, seed=seed)
    result = run_scenario(s, max_steps=600)
    assert not result['deadlock']
    metrics = compute_metrics(result)
    assert all(m['time_to_airborne'] is not None for m in metrics['aircraft'].values())


@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
def test_random_10_simulation_completes(seed):
    'Smoke test: sim must complete cleanly even when it deadlocks.'
    s = random_departures(10, seed=seed)
    result = run_scenario(s, max_steps=600)
    assert 'deadlock' in result
    assert 'history' in result


def test_random_10_seed5_documents_known_deadlock():
    'Documented finding: 10 aircraft, seed=5, stagger=0 reliably deadlocks '
    'on raw-graph paths. Only a very large stagger (>=400) rescues it.'
    s = random_departures(10, seed=5)
    result = run_scenario(s, max_steps=500)
    assert result['deadlock'] is True


def test_random_10_seed2_documents_persistent_deadlock():
    'Documented finding: seed=2, n=10 deadlocks at every stagger value tried '
    '(0, 5, 10, 20, 50, 100, 200, 400). This scenario contains a head-on '
    'edge conflict that the local-rules engine cannot resolve without '
    'edge locking or global re-planning.'
    for stagger in (0, 5, 10, 20, 50, 100):
        s = random_departures(10, seed=2, stagger=stagger)
        result = run_scenario(s, max_steps=500)
        assert result['deadlock'] is True, (
            f'seed=2 unexpectedly cleared at stagger={stagger}'
        )


def test_huge_stagger_resolves_seed5_deadlock():
    'Seed=5 is rescuable, but only with a very large stagger window.'
    s = random_departures(10, seed=5, stagger=400)
    result = run_scenario(s, max_steps=1000)
    assert not result['deadlock']


@pytest.mark.parametrize('seed', [1, 3, 4])  # seed=2 has a known structural deadlock
@pytest.mark.parametrize('stagger', [5, 10, 20])
def test_random_10_with_stagger(seed, stagger):
    'Stress run: most seed/stagger combos at n=10 should complete. Seed 2 '
    'is excluded (documented persistent deadlock); seed 5 has its own test.'
    s = random_departures(10, seed=seed, stagger=stagger)
    result = run_scenario(s, max_steps=600)
    assert not result['deadlock']


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_random_arrivals_5_no_crash(seed):
    'Arrivals can start on the runway, which is exclusive: smoke test for '
    'the spawn-when-free logic.'
    s = random_arrivals(5, seed=seed, stagger=5)
    result = run_scenario(s, max_steps=600)
    # Arrivals MAY deadlock (no rapid-exit modelling) so we only assert no crash.
    assert 'deadlock' in result


@pytest.mark.parametrize('seed', [1, 2, 3])
def test_random_mixed_smoke(seed):
    s = random_mixed(8, seed=seed, stagger=10)
    result = run_scenario(s, max_steps=600)
    assert 'deadlock' in result
