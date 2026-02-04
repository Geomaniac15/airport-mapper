from collections import deque, defaultdict
import time
import heapq

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

def dijkstra_path(graph_w, start, goal):
    pq = [(0.0, start)]
    dist = {start: 0.0}
    prev = {start: None}

    while pq:
        d, u = heapq.heappop(pq)

        if u == goal:
            break

        if d > dist[u]:
            continue

        for v, w in graph_w[u].items():
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    
    if goal not in prev:
        return None
    
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]

    return list(reversed(path))

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