# JFK Graph scenarios using real node IDs from the largest connected component
# Stands in main component: N789, N804, N805, N806, N808, etc.
# Runways in main component: N1, N2, N3, N4, N5, etc.

SCENARIOS = {
    'two_departures': [
        { 'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N1' },
        { 'aircraft_id': 'A2', 'start': 'N804', 'goal': 'N2' },
    ],
    'three_departures': [
        { 'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N45' },
        { 'aircraft_id': 'A2', 'start': 'N804', 'goal': 'N1' },
        { 'aircraft_id': 'A3', 'start': 'N993', 'goal': 'N2' },
    ],
    'stand_swap': [
        { 'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N804' },
        { 'aircraft_id': 'A2', 'start': 'N804', 'goal': 'N789' },
    ],
    # backward-compatible scenario names expected by tests
    'simple_departures': [
        { 'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N1' },
        { 'aircraft_id': 'A2', 'start': 'N804', 'goal': 'N2' },
    ],
    'swap_positions': [
        { 'aircraft_id': 'A1', 'start': 'N14', 'goal': 'N15' },
        { 'aircraft_id': 'A2', 'start': 'N15', 'goal': 'N14' },
    ],
    'runway_contention': [
        { 'aircraft_id': 'A1', 'start': 'N789', 'goal': 'N45' },
        { 'aircraft_id': 'A2', 'start': 'N804', 'goal': 'N1' },
        { 'aircraft_id': 'A3', 'start': 'N993', 'goal': 'N2' },
    ],
}

scenario_names = list(SCENARIOS.keys())
