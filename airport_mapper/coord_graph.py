from collections import defaultdict

def build_graph_from_polylines(polylines, decimals=5):
    '''
    polylines: list[list[tuple[float, float]]]
        A list of polylines, where each polyline is a list of (x, y) coordinates.
    returns:
        graph: dict[str, list[str]] adjacency representation of the graph
        node_pos: dict[str, tuple[float, float]] node -> (x, y) position mapping
    '''

    point_to_node = {}
    node_pos = {}
    next_id = 0

    def get_node_id(point, decimals):
        nonlocal next_id
        key = (round(point[0], decimals), round(point[1], decimals))
        # HAS TO BE KEY NOT IN, not point
        if key not in point_to_node:
            node_id = f'N{next_id}'
            point_to_node[key] = node_id
            node_pos[node_id] = key
            next_id += 1
        # print(point_to_node)
        # print('\n')
        return point_to_node[key]
    
    graph = defaultdict(set)  # has to be a set to avoid duplicate edges

    for line in polylines:
        if len(line) < 2:
            continue
        for a, b in zip(line, line[1:]):
            na = get_node_id(a, decimals=4)
            nb = get_node_id(b, decimals=4)

            if na == nb:
                continue

            graph[na].add(nb)
            graph[nb].add(na)

    
    graph = {k: sorted(v) for k, v in graph.items()}
    return graph, node_pos


if __name__ == '__main__':
    taxiways = [
        [(0, 0), (0, 10), (10, 10)],
        [(0, 10), (-5, 10)],
        [(10, 10), (10, 15)],
    ]

    graph, pos = build_graph_from_polylines(taxiways)
    print('graph:', graph)
    print('node positions:', pos)