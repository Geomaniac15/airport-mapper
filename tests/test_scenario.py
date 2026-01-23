from airport_mapper.main_sim import run_scenario
from airport_mapper.scenarios import SCENARIOS

def test_simple_departures():
    result = run_scenario(SCENARIOS['simple_departures'])
    assert not result['deadlock']
    assert all(ac.removed for ac in result['aircraft'])

def test_swap_positions_deadlock():
    result = run_scenario(SCENARIOS['swap_positions'])
    assert result['deadlock']

def test_runway_contention():
    result = run_scenario(SCENARIOS['runway_contention'])
    assert not result['deadlock']
    assert all(ac.removed for ac in result['aircraft'])