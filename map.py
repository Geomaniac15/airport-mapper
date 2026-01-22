#  deque for FIFO queue, used for BFS
#  defaultdict for grouping aircraft by requested node
from collections import deque, defaultdict
import time

class Node:
    # represents a place in the airport
    def __init__(self, name, exclusive=False):
        self.name = name
        self.exclusive = exclusive  # only one aircraft may occupy this node at a time
        self.occupied_by = None  # aircraft id or None
    
    def is_free(self):
        return self.occupied_by is None
    
class Aircraft:
    def __init__(self, aircraft_id, start_node, goal_node, path):
        self.id = aircraft_id
        self.current = start_node
        self.goal = goal_node
        self.path = path
        self.path_index = 0  # how far along the path it is
        self.waiting = False
        self.done = False
        self.removed = False
        self.lookahead = 3  # how many nodes ahead to consider for corridor proposal

    def step(self):
        if self.path_index + 1 >= len(self.path):
            return  # already at destination
        
        next_node = self.path[self.path_index + 1]

        if next_node.exclusive and not next_node.is_free():
            self.waiting = True
            return
        
        # Move
        self.current.occupied_by = None
        next_node.occupied_by = self.id
        self.current = next_node
        self.path_index += 1
        self.waiting = False

    def propose_next(self):
        # propose what node the aircraft wants next
        if self.done:
            return None
        
        if self.path_index + 1 >= len(self.path):
            return None  # no move, already at goal
        
        return self.path[self.path_index + 1]
    
    def propose_corridor(self, k=None):
        # return a list of nodes representing the corridor the aircraft wants to reserve

        if self.done or self.removed:
            return None
        
        if k is None:
            k = self.lookahead
        
        # next nodes along the path (skips current node)
        start = self.path_index + 1
        end = start + k

        corridor = self.path[start:end]
        return corridor if corridor else None

def corridor_is_clear(corridor):
    if corridor is None:
        return True
    for node in corridor:
        if node.exclusive and not node.is_free():
            return False
    return True

def bfs_path(graph, start, goal):
    # Queue of nodes to explore
    queue = deque([start])

    # Parent dict to reconstruct path
    parent = {start: None}

    while queue:
        current = queue.popleft()

        # Stop when goal is reached
        if current == goal:
            break

        # Loop through all neighbours
        for neighbour in graph[current]:
            # Only visit each node once
            if neighbour not in parent:
                parent[neighbour] = current
                queue.append(neighbour)
    
    if goal not in parent:
        return None
    
    # Reconstruct path by walking backwards
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    
    path.reverse()
    return path

def collect_proposals(aircraft_list):
    # where does each aircraft want to go
    proposals = {}
    for ac in aircraft_list:
        if ac.removed:
            continue
        next_node = ac.propose_next()
        corridor = ac.propose_corridor()
        if next_node:
            proposals[ac.id] = (ac, next_node, corridor)
    
    # print("Proposals:", {ac_id: node.name for ac_id, (ac, node) in proposals.items()})
    return proposals

def resolve_conflicts(proposals):
    # who is allowed to move
    node_requests = defaultdict(list)

    # eligible to move?
    eligible = []

    # group requests by node
    for ac, next_node, corridor in proposals.values():
        if corridor_is_clear(corridor):
            eligible.append((ac, next_node))

        # normal case: at least one aircraft eligible
        if eligible:
            for ac, next_node in eligible:
                node_requests[next_node].append(ac)
        else:
            # escape hatch: one aircfraft can go
            # its next node must be free tho
            candidates = []
            for ac, next_node, _corridor in proposals.values():
                if (not next_node.exclusive) or next_node.is_free():
                    candidates.append((ac, next_node))
            if candidates:
                ac, next_node = sorted(candidates, key=lambda x: x[0].id)[0]
                node_requests[next_node].append(ac)
    
    approved = set()

    for node, requesters in node_requests.items():
        # block entry if already occupied
        # two aircraft cannot be on the runway at the same time
        if node.exclusive and not node.is_free():
            continue
        
        if not node.exclusive:
            # everyone can go
            for ac in requesters:
                approved.add(ac.id)
        else:
            # aircraft with lowest id wins
            winner = sorted(requesters, key=lambda a: a.id)[0]
            approved.add(winner.id)
    
    return approved

def commit_moves(proposals, approved):
    # execute moves
    for ac_id, (ac, next_node, _corridor) in proposals.items():
        if ac_id not in approved:
            continue

        # move
        ac.current.occupied_by = None
        next_node.occupied_by = ac.id
        ac.current = next_node
        ac.path_index += 1 
        
        if ac.current.name == 'RWY':
            ac.done = True

def loc(ac):
    return 'AIRBORNE' if ac.removed else ac.current.name

graph = {
    # Stands
    'S1': ['I1'],
    'S2': ['I2'],

    # Intersections
    'I1': ['S1', 'I3'],
    'I2': ['S2', 'I5'],
    'I3': ['I1', 'I2', 'I4', 'I5'],
    'I4': ['I1', 'I3', 'R1'],
    'I5': ['I2', 'I3', 'R2'],

    # Runway Access Points
    'R1': ['I4', 'RWY'],
    'R2': ['I5', 'RWY'],

    # Runway
    'RWY': ['R1', 'R2'],
}

exclusive_nodes = {'I1','I2', 'I3', 'I4', 'I5', 'R1', 'R2', 'RWY'}

nodes = {
    name: Node(name, exclusive=(name in exclusive_nodes))
    for name in graph
}

SCENARIO = [
    { 'aircraft_id': 'A1', 'start': 'S1', 'goal': 'S2' },
    { 'aircraft_id': 'A2', 'start': 'S2', 'goal': 'S1' },
]

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
    moved_this_step = False

    # 0. debug for proposal and lookahead functionality
    if ac.removed:
        continue
    nxt = ac.propose_next()
    corridor = ac.propose_corridor(2)  # force lookahead of 2
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
        moved_this_step = True
    

    # 4. commit moves phase
    commit_moves(proposals, approved)

    # for ac in aircraft_list:
    #     if ac.removed:
    #         continue
    #     if ac.current is not ac.path[ac.path_index]:
    #         raise RuntimeError(
    #             f'{ac.id} mismatch: current={ac.current.name} path_index={ac.path_index} path_node={ac.path[ac.path_index].name}'
    #         )

    if all(ac.propose_next() is None or ac.removed for ac in aircraft_list):
        print("All aircraft finished. Stopping simulation.")
        break


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

    # time.sleep(0.75)

# print(bfs_path(graph, 'S1', 'R2')) # Works
# print(bfs_path(graph, 'S2', 'R2'))