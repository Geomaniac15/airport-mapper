from collections import deque
import time

class Node:
    def __init__(self, name, exclusive=False):
        self.name = name
        self.exclusive = exclusive
        self.occupied_by = None  # aircraft id or None
    
    def is_free(self):
        return self.occupied_by is None
    
class Aircraft:
    def __init__(self, aircraft_id, start_node, goal_node, path):
        self.id = aircraft_id
        self.current = start_node
        self.goal = goal_node
        self.path = path
        self.path_index = 0
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
    name: Node(name, exclusive=(name in {'I3', 'I4', 'I5'}))
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

path1 = bfs_path(graph, 'S1', 'R2')
path2 = bfs_path(graph, 'S2', 'R1')

aircraft1 = Aircraft('A1', nodes['S1'], nodes['R1'], [nodes[n] for n in path1])
aircraft2 = Aircraft('A2', nodes['S2'], nodes['R2'], [nodes[n] for n in path2])

nodes['S1'].occupied_by = 'A1'
nodes['S2'].occupied_by = 'A2'

for t in range(5):
    aircraft1.step()
    aircraft2.step()
    print(f't={t}: A1 at {aircraft1.current.name}, A2 at {aircraft2.current.name}')
    time.sleep(0.75)

# print(bfs_path(graph, 'S1', 'R2')) # Works
# print(bfs_path(graph, 'S2', 'R2'))