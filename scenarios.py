SCENARIOS = {
    'simple_departures': [
        { 'aircraft_id': 'A1', 'start': 'S1', 'goal': 'RWY' },
        { 'aircraft_id': 'A2', 'start': 'S2', 'goal': 'RWY' },
    ],
    'swap_positions': [
        { 'aircraft_id': 'A1', 'start': 'S1', 'goal': 'S2' },
        { 'aircraft_id': 'A2', 'start': 'S2', 'goal': 'S1' },
    ],
    'runway_contention': [
        { 'aircraft_id': 'A1', 'start': 'S1', 'goal': 'RWY' },
        { 'aircraft_id': 'A2', 'start': 'S2', 'goal': 'RWY' },
        { 'aircraft_id': 'A3', 'start': 'S3', 'goal': 'RWY' },
    ],
}

scenario_names = list(SCENARIOS.keys())
