from collections import defaultdict

def build_graph_from_polylines(polylines, decimals=5):
    '''
    polylines: list[list[tuple[float, float]]]
        A list of polylines, where each polyline is a list of (x, y) coordinates.
    returns:
        graph: dict[str, list[str]] adjacency representation of the graph
        node_pos: dict[str, tuple[float, float]] node -> (x, y) position mapping
    '''

    key_to_node = {}
    node_pos = {}
    next_id = 0

    def get_node_id(point, decimals):
        nonlocal next_id
        key = (round(point[0], decimals), round(point[1], decimals))
        # HAS TO BE KEY NOT IN, not point
        if key not in key_to_node:
            node_id = f'N{next_id}'
            key_to_node[key] = node_id
            node_pos[node_id] = key
            next_id += 1
        # print(key_to_node)
        # print('\n')
        return key_to_node[key]
    
    graph = defaultdict(lambda: defaultdict(set))  # has to be a set to avoid duplicate edges
    
    def add_edge(a, b, aeroway_type):
        if a == b:
            return
        graph[a][b].add(aeroway_type)
        graph[b][a].add(aeroway_type)

    for item in polylines:
        coords = item.get('coords', [])
        aeroway_type = item.get('aeroway')
        if not aeroway_type or len(coords) < 2:
            continue


        for p, q in zip(coords, coords[1:]):
            na = get_node_id(p, decimals)
            nb = get_node_id(q, decimals)
            add_edge(na, nb, aeroway_type)


    frozen ={
        n: {nbr: set(types) for nbr, types in nbrs.items()}
        for n, nbrs in graph.items()
    }
    return frozen, node_pos, key_to_node


if __name__ == '__main__':
    taxiways = [
        [(0, 0), (0, 10), (10, 10)],
        [(0, 10), (-5, 10)],
        [(10, 10), (10, 15)],
    ]

    graph, pos = build_graph_from_polylines(taxiways)
    print('graph:', graph)
    print('node positions:', pos)