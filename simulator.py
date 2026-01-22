#  deque for FIFO queue, used for BFS
#  defaultdict for grouping aircraft by requested node
from collections import deque, defaultdict
import time

from models import Node, Aircraft
from graph import graph, exclusive_nodes, draw_graph
from planning import bfs_path, corridor_is_clear, collect_proposals
from rules import is_blocked, block_reason, resolve_conflicts, commit_moves
from scenarios import SCENARIOS, scenario_names


def loc(ac):
    return 'AIRBORNE' if ac.removed else ac.current.name




def build_nodes():
    return {name: Node(name, exclusive=(name in exclusive_nodes)) for name in graph}

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

        ac = Aircraft(
            spec['aircraft_id'],
            nodes[start],
            nodes[goal],
            [nodes[n] for n in path]
        )

        ac.current.occupied_by = ac.id
        aircraft_list.append(ac)

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

    for t in range(100):

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

        # 2. proposal phase   
        proposals = collect_proposals(aircraft_list)

        # 3. conflict resolution phase
        approved = resolve_conflicts(proposals)

        if approved:
            moved_this_step = commit_moves(proposals, approved)  # reset each step
        
        # track wait times
        for ac in aircraft_list:
            if is_blocked(ac, approved):
                ac.wait_ticks += 1
            else:
                ac.wait_ticks = 0

        # 4. commit moves phase
        commit_moves(proposals, approved)

        for ac in aircraft_list:
            if is_blocked(ac, approved):
                reason = block_reason(ac, approved)
                print(f'{ac.id} condition: {reason}, wait_ticks: {ac.wait_ticks}')

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
    for scenario_name in scenario_names:
        print(f"Running scenario: {scenario_name}")
        main_sim(SCENARIOS[scenario_name])
        print("\n")