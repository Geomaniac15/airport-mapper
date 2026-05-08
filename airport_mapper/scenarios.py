'''Hand-authored and procedurally generated scenarios.

SCENARIOS holds named scenarios with hand-picked JFK node IDs that exercise
specific behaviours (deadlock, runway contention, stand swap, etc.).

random_departures, random_arrivals, and random_mixed generate scenarios on
the fly from the loaded graph. They validate path reachability so every
generated aircraft has a realisable route.
'''

import random


# JFK Graph scenarios using real node IDs from the largest connected component
# Stands in main component: N789, N804, N805, N806, N808, etc.
# Runways in main component: N1, N2, N3, N4, N5, etc.

SCENARIOS = {
    "two_departures": [
        {"aircraft_id": "A1", "start": "N789", "goal": "N1"},
        {"aircraft_id": "A2", "start": "N804", "goal": "N2"},
    ],
    "three_departures": [
        {"aircraft_id": "A1", "start": "N789", "goal": "N45"},
        {"aircraft_id": "A2", "start": "N804", "goal": "N1"},
        {"aircraft_id": "A3", "start": "N993", "goal": "N2"},
    ],
    "stand_swap": [
        {"aircraft_id": "A1", "start": "N789", "goal": "N804"},
        {"aircraft_id": "A2", "start": "N804", "goal": "N789"},
    ],
    # backward-compatible scenario names expected by tests
    "simple_departures": [
        {"aircraft_id": "A1", "start": "N789", "goal": "N1"},
        {"aircraft_id": "A2", "start": "N804", "goal": "N2"},
    ],
    "swap_positions": [
        {"aircraft_id": "A1", "start": "N14", "goal": "N15"},
        {"aircraft_id": "A2", "start": "N15", "goal": "N14"},
    ],
    "runway_contention": [
        {"aircraft_id": "A1", "start": "N789", "goal": "N45"},
        {"aircraft_id": "A2", "start": "N804", "goal": "N1"},
        {"aircraft_id": "A3", "start": "N993", "goal": "N2"},
    ],
}

scenario_names = list(SCENARIOS.keys())


def _aircraft_id(i):
    return f'A{i + 1}'


def _generate_pairs(starts_pool, goals_pool, n, rng, allow_repeat_starts=False):
    'Sample n start->goal pairs that have a realisable Dijkstra path.'

    from airport_mapper.graph import get_compressed_graph
    from airport_mapper.planning import dijkstra_path

    compressed = get_compressed_graph()

    starts = sorted(starts_pool)
    goals = sorted(goals_pool)

    if not starts or not goals:
        raise ValueError(
            f'cannot generate scenario: '
            f'{len(starts)} starts, {len(goals)} goals available'
        )

    pairs = []
    used_starts = set()
    max_attempts = max(n * 30, 200)
    attempts = 0

    while len(pairs) < n and attempts < max_attempts:
        attempts += 1
        start = rng.choice(starts)
        if not allow_repeat_starts and start in used_starts:
            continue
        goal = rng.choice(goals)
        if start == goal:
            continue
        if dijkstra_path(compressed, start, goal) is None:
            continue
        used_starts.add(start)
        pairs.append((start, goal))

    if len(pairs) < n:
        raise ValueError(
            f'could only generate {len(pairs)} of {n} requested aircraft '
            f'after {attempts} attempts (graph connectivity may be sparse)'
        )

    return pairs


def _spawn_ticks(n, rng, stagger):
    'Sample n spawn ticks uniformly in [0, stagger]. stagger=0 -> all zero.'

    if stagger <= 0:
        return [0] * n
    return [rng.randint(0, stagger) for _ in range(n)]


def random_departures(n, seed=None, stagger=0):
    '''Generate n stand -> runway departures with validated paths.

    If stagger > 0, each aircraft is given a spawn_tick chosen uniformly in
    [0, stagger], modelling staggered pushbacks rather than a simultaneous
    rush at t=0.
    '''

    from airport_mapper.graph import runway_nodes, stand_nodes
    rng = random.Random(seed)
    pairs = _generate_pairs(stand_nodes, runway_nodes, n, rng)
    spawns = _spawn_ticks(n, rng, stagger)
    return [
        {
            'aircraft_id': _aircraft_id(i),
            'start': s,
            'goal': g,
            'spawn_tick': st,
        }
        for i, ((s, g), st) in enumerate(zip(pairs, spawns))
    ]


def random_arrivals(n, seed=None, stagger=0):
    '''Generate n runway -> stand arrivals with validated paths.

    Note: this is an idealisation. Real arrivals exit the runway via a
    rapid-exit taxiway rather than starting on the runway centreline.
    '''

    from airport_mapper.graph import runway_nodes, stand_nodes
    rng = random.Random(seed)
    pairs = _generate_pairs(
        runway_nodes, stand_nodes, n, rng, allow_repeat_starts=True,
    )
    spawns = _spawn_ticks(n, rng, stagger)
    return [
        {
            'aircraft_id': _aircraft_id(i),
            'start': s,
            'goal': g,
            'spawn_tick': st,
        }
        for i, ((s, g), st) in enumerate(zip(pairs, spawns))
    ]


def random_mixed(n, seed=None, stagger=0):
    'Generate n aircraft, alternating departures and arrivals.'

    rng = random.Random(seed)
    n_dep = (n + 1) // 2
    n_arr = n - n_dep
    deps = random_departures(
        n_dep, seed=rng.randint(0, 2**31 - 1), stagger=stagger,
    )
    arrs = random_arrivals(
        n_arr, seed=rng.randint(0, 2**31 - 1), stagger=stagger,
    )

    # Interleave so the IDs aren't all-departures-first.
    merged = []
    for i in range(max(len(deps), len(arrs))):
        if i < len(deps):
            merged.append(deps[i])
        if i < len(arrs):
            merged.append(arrs[i])
    # Renumber sequentially after the interleave.
    for i, spec in enumerate(merged):
        spec['aircraft_id'] = _aircraft_id(i)
    return merged
