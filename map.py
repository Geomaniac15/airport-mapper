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
        if self.path_index + 1 >= len(self.path):
            return None  # no move, already at goal
        
        return self.path[self.path_index + 1]

graph = {
    # Stands
    'S1': ['I1'],
    'S2': ['I2'],

    # Intersections
    'I1': ['S1', 'I4', 'I3'],
    'I2': ['S2', 'I5', 'I3'],
    'I3': ['I1', 'I2', 'I4', 'I5'],
    'I4': ['I1', 'I3', 'R1'],
    'I5': ['I2', 'I3', 'R2'],

    # Runway Access Points
    'R1': ['I4'],
    'R2': ['I5'],
}

nodes = {
    name: Node(name, exclusive=(name in {'I3', 'I4', 'I5', 'R1', 'R2'}))
    for name in graph
}

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
        next_node = ac.propose_next()
        if next_node:
            proposals[ac.id] = (ac, next_node)
    return proposals

def resolve_conflicts(proposals):
    # who is allowed to move
    node_requests = defaultdict(list)

    # group requests by node
    for ac, node in proposals.values():
        node_requests[node].append(ac)
    
    approved = set()

    for node, requesters in node_requests.items():
        # block entry if already occupied
        # two aircraft cannot be on the runway at the same time
        if node.exclusive and not node.is_free():
            continue
        
        if not node.exclusive:
            for ac in requesters:
                approved.add(ac.id)
        else:
            # aircraft with lowest id wins
            winner = sorted(requesters, key=lambda a: a.id)[0]
            approved.add(winner.id)
    
    return approved

def commit_moves(proposals, approved):
    # execute moves
    for ac_id, (ac, next_node) in proposals.items():
        if ac_id in approved:
            ac.current.occupied_by = None
            next_node.occupied_by = ac.id
            ac.current = next_node
            ac.path_index += 1

path1 = bfs_path(graph, 'S1', 'R1')
path2 = bfs_path(graph, 'S2', 'R1')

aircraft1 = Aircraft('A1', nodes['S1'], nodes['R1'], [nodes[n] for n in path1])
aircraft2 = Aircraft('A2', nodes['S2'], nodes['R2'], [nodes[n] for n in path2])

nodes['S1'].occupied_by = 'A1'
nodes['S2'].occupied_by = 'A2'

aircraft_list = [aircraft1, aircraft2]

for t in range(6):
    proposals = collect_proposals(aircraft_list)
    approved = resolve_conflicts(proposals)
    commit_moves(proposals, approved)

    print(f't={t}: A1 at {aircraft1.current.name}, A2 at {aircraft2.current.name}')
    time.sleep(0.75)

# print(bfs_path(graph, 'S1', 'R2')) # Works
# print(bfs_path(graph, 'S2', 'R2'))