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
    for ac in aircraft_list:
        print(f'{ac.id}: removed={ac.removed}, done={ac.done}, current={loc(ac)}')

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

def main_sim(SCENARIO):
    nodes = build_nodes()
    aircraft_list = []

    for spec in SCENARIO:
        start = spec['start']
        goal = spec['goal']

        path = bfs_path(graph, start, goal)
        if path is None:
            raise ValueError(f"No path for {spec['aircraft_id']} from {start} to {goal}")

        # ac = Aircraft(
        #     spec['aircraft_id'],
        #     nodes[start],
        #     nodes[goal],
        #     [nodes[n] for n in path]
        # )
        ac = Aircraft(spec['aircraft_id'], None, None, [nodes[n] for n in path])

        ac.path_index = 0
        ac.current = ac.path[0]
        ac.goal = ac.path[-1].name
        ac.current.occupied_by = ac.id
        
        aircraft_list.append(ac)

    # print(spec['aircraft_id'], 'path:', ' -> '.join(path))
    assert path[-1] == goal, f'{spec["aircraft_id"]} path ends at {path[-1]}  not {goal}'

    occupied = set()
    for ac in aircraft_list:
        if ac.current.name in occupied:
            raise ValueError(f'Node {ac.current.name} occupied by multiple aircraft at start')
        occupied.add(ac.current.name)

    # path1 = bfs_path(graph, aircraft_starting_positions['S1'], 'RWY')
    # path2 = bfs_path(graph, aircraft_starting_positions['S2'], 'RWY')

    # aircraft1 = Aircraft('A1', nodes['RWY'], nodes['S1'], [nodes[n] for n in path1])
    # aircraft2 = Aircraft('A2', nodes['RWY'], nodes['S2'], [nodes[n] for n in path2])

    # nodes['S1'].occupied_by = 'A1'
    # nodes['S2'].occupied_by = 'A2'

    # aircraft_list = [aircraft1, aircraft2]

    no_progress_steps = 0

    for t in range(10):

        # 0. debug for proposal and lookahead functionality
        # if ac.removed:
        #     continue
        # nxt = ac.propose_next()
        # corridor = ac.propose_corridor(2)  # force lookahead of 2
        # for ac in aircraft_list:
        #     print(ac.id, 'at', ac.current.name,
        #         '\nnext:', (nxt.name if nxt else None),
        #         '\ncorridor:', [n.name for n in corridor] if corridor else None)

        # 1. cleanup phase (end-of-runway effects)
        for ac in aircraft_list:
            if ac.done and not ac.removed:
                ac.current.occupied_by = None
                ac.removed = True
                # to add: move ac off-map or mark as removed/taken off

        for ac in aircraft_list:
            if ac.removed:
                assert ac.current.occupied_by is None, f"{ac.id} removed but still occupying {ac.current.name}"
            

        # 2. proposal phase   
        proposals = collect_proposals(aircraft_list)

        # print('RWY occupied by:', nodes['RWY'].occupied_by)

        # 3. conflict resolution phase
        approved = resolve_conflicts(proposals)

        # 4. commit moves phase
        moved_this_step = commit_moves(proposals, approved)

        # sanity check for a1 cause this is driving me insane
        a1 = proposals.get('A1')
        if a1:
            ac, next_node, corridor = a1
            # print(f'''A1 debug:
            #       Current: {ac.current.name}
            #       path_index: {ac.path_index}
            #       path_node: {ac.path[ac.path_index].name}
            #       next_node: {next_node.name}
            #       expected_next: {ac.path[ac.path_index + 1].name if ac.path_index + 1 < len(ac.path) else None}
            #       corridor: {[n.name for n in corridor] if corridor else None}''')

        for ac in aircraft_list:
            if ac.removed:
                continue
            expected = ac.path[ac.path_index]
            if ac.current is not expected:
                raise RuntimeError(
                    f'{ac.id} mismatch after move commit: current={ac.current.name} path_index={ac.path_index} expected={expected.name}'
                )
            # if is_blocked(ac, approved):
            #     reason = block_reason(ac, approved)
            #     print(f'{ac.id} condition: {reason}, wait_ticks: {ac.wait_ticks}')
            # if ac.id == 'A2' and not ac.removed:
            #     print('A2 next:', ac.propose_next().name if ac.propose_next() else None)
            #     print('A2 reason:', block_reason(ac, approved))

        # for ac in aircraft_list:
        #     if ac.removed:
        #         continue
        #     if ac.current is not ac.path[ac.path_index]:
        #         raise RuntimeError(
        #             f'{ac.id} mismatch: current={ac.current.name} path_index={ac.path_index} path_node={ac.path[ac.path_index].name}'
        #         )


        # 5. check for deadlock
        if not moved_this_step:
            no_progress_steps += 1
            if no_progress_steps >= 3:
                print("Deadlock detected, stopping simulation.")
                break
        else:
            no_progress_steps = 0

        # 6. observation
        #print(f't={t}: A1 at {loc(aircraft1)}, A2 at {loc(aircraft2)}')
        
        print(f"t={t}: " +
            ", ".join(
                f"{ac.id} at {loc(ac)}" for ac in aircraft_list)
            )
        
        if all(ac.removed for ac in aircraft_list):
            print("All aircraft finished. Stopping simulation.")
            break

        # time.sleep(0.75)

    # print(bfs_path(graph, 'S1', 'R2')) # Works
    # print(bfs_path(graph, 'S2', 'R2'))



if __name__ == "__main__":
    result = run_scenario(SCENARIOS['simple_departures'])
    print_events(result['history'], limit=30)
    print('\n')
    print_timeline(result['history'], 'A1')
    print('\n')
    plot_wait_ticks(result['history'])


    # for scenario_name in scenario_names:
    #     print(f"Running scenario: {scenario_name}")
    #     main_sim(SCENARIOS[scenario_name])
    #     print("\n")