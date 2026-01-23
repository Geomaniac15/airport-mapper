#  deque for FIFO queue, used for BFS
#  defaultdict for grouping aircraft by requested node
from collections import deque, defaultdict
import time
import matplotlib.pyplot as plt

from airport_mapper.models import Node, Aircraft
from airport_mapper.graph import graph, exclusive_nodes, draw_graph
from airport_mapper.planning import bfs_path, corridor_is_clear, collect_proposals
from airport_mapper.rules import is_blocked, block_reason, resolve_conflicts, commit_moves
from airport_mapper.scenarios import SCENARIOS, scenario_names


def loc(ac):
    return 'AIRBORNE' if ac.removed else ac.current.name

def build_nodes():
    return {name: Node(name, exclusive=(name in exclusive_nodes)) for name in graph}

def run_scenario(
    scenario,
    max_steps=200,
):
    aircraft_list = []
    nodes = build_nodes()

    for spec in scenario:
        start = spec['start']
        goal = spec['goal']

        path = bfs_path(graph, start, goal)
        if path is None:
            raise ValueError(f"No path for {spec['aircraft_id']} from {start} to {goal}")

        ac = Aircraft(spec['aircraft_id'], None, None, [nodes[n] for n in path])

        ac.path_index = 0
        ac.current = ac.path[0]
        ac.goal = ac.path[-1]
        ac.current.occupied_by = ac.id

        aircraft_list.append(ac)

    no_progress = 0
    deadlock = False

    history = {
        'positions': {ac.id: [] for ac in aircraft_list},
        'wait_ticks': {ac.id: [] for ac in aircraft_list},
        'events': [],
    }

    for t in range(max_steps):
        for ac in aircraft_list:
            if ac.done and not ac.removed:
                ac.current.occupied_by = None
                ac.removed = True
        
        proposals = collect_proposals(aircraft_list)
        approved = resolve_conflicts(proposals)

        for ac in aircraft_list:
            if ac.removed or ac.done:
                ac.wait_ticks = 0
                continue
            
            if ac.propose_next() is None:
                ac.wait_ticks = 0
                continue

            if ac.id in approved:
                ac.wait_ticks = 0
            else:
                ac.wait_ticks += 1

        moved = commit_moves(proposals, approved)

        event = {
            't': t,
            'moved': [],
            'blocked': {},
        }

        for ac in aircraft_list:
            history['positions'][ac.id].append(loc(ac))
            history['wait_ticks'][ac.id].append(ac.wait_ticks)

            if ac.id in approved:
                event['moved'].append(ac.id)
            elif is_blocked(ac, approved):
                reason = block_reason(ac, approved)
                event['blocked'][ac.id] = reason

            if not ac.done and ac.current is ac.goal:
                ac.done = True

        if event['moved'] or event['blocked']:
            history['events'].append(event)
        

        if moved:
            no_progress = 0
        else:
            no_progress += 1
            if no_progress >= 3:
                deadlock = True
                break

        if all(ac.removed for ac in aircraft_list):
            break

    print(f'Scenario completed in {t} steps. Deadlock: {deadlock}')
    # for ac in aircraft_list:
    #     print(f'{ac.id}: removed={ac.removed}, done={ac.done}, current={loc(ac)}')

    return {
        'aircraft': aircraft_list,
        'deadlock': deadlock,
        'steps': t,
        'history': history,
    }

def print_events(history, limit=None):
    events = history['events'][:limit]
    for e in events:
        moved = ",".join(e['moved'])
        blocked = ", ".join(f"{k}:{v}" for k,v in e['blocked'].items())
        print(f"t={e['t']:>3} | moved=[{moved}] | blocked=[{blocked}]")

def print_timeline(history, aircraft_id):
    for t, pos in enumerate(history['positions'][aircraft_id]):
        print(f't={t:>3}: {aircraft_id} at {pos}')

def plot_wait_ticks(history):
    ticks = range(len(next(iter(history['wait_ticks'].values()))))

    for ac_id, wait_list in history['wait_ticks'].items():
        plt.plot(ticks, wait_list, label=ac_id)
    
    plt.xlabel('Time Step')
    plt.ylabel('Wait Ticks')
    plt.legend()
    plt.show()

# draw_graph(graph)

if __name__ == "__main__":
    print('\n')
    # result = run_scenario(SCENARIOS['simple_departures'])
    # print_events(result['history'], limit=30)
    # print('\n')
    # print_timeline(result['history'], 'A1')
    # print('\n')
    # plot_wait_ticks(result['history'])


    for scenario_name in scenario_names:
        print(f"Running scenario: {scenario_name}")
        result = run_scenario(SCENARIOS[scenario_name])
        if 'A1' in [ac.id for ac in result['aircraft']]:
            print_timeline(result['history'], 'A1')
            print("\n")
        if 'A2' in [ac.id for ac in result['aircraft']]:
            print_timeline(result['history'], 'A2')
            print("\n")
        if 'A3' in [ac.id for ac in result['aircraft']]:
            print_timeline(result['history'], 'A3')
            print("\n")