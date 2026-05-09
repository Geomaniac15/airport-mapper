import json
import math
import os

import matplotlib.pyplot as plt

from airport_mapper.polyline_to_graph import haversine_m

HERE = os.path.dirname(__file__)
AIRPORTS_DIR = os.path.join(HERE, 'airports')
DEFAULT_IATA = 'JFK'

# These globals are bound by load_airport(). Defaults are filled in at the
# bottom of this module via load_airport(DEFAULT_IATA) so existing code that
# imports `graph`, `node_types`, etc. continues to work unchanged.
graph = None
node_types = None
node_pos = None
exclusive_nodes = None
stand_nodes = None
runway_nodes = None
current_iata = None

# Lazy cache of the compressed weighted graph used for path planning.
# Invalidated whenever the airport changes.
_compressed_graph_cache = None
_compressed_chains_cache = None


def _airport_path(iata):
    return os.path.join(AIRPORTS_DIR, f'{iata.upper()}.json')


def available_airports():
    'List IATA codes for which a labelled graph file is present on disk.'
    if not os.path.isdir(AIRPORTS_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(AIRPORTS_DIR)
        if f.endswith('.json') and not f.endswith('.overpass.json')
    )


def load_airport(iata):
    '''Bind module-level graph globals to the given airport.

    Reads airports/<IATA>.json (created by polyline_to_graph.build_airport_graph)
    and rebinds graph, node_types, node_pos, the node-class sets, and the
    compressed-graph caches.
    '''
    global graph, node_types, node_pos
    global exclusive_nodes, stand_nodes, runway_nodes
    global current_iata
    global _compressed_graph_cache, _compressed_chains_cache

    iata = iata.upper()
    path = _airport_path(iata)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No graph file for {iata!r} at {path}. "
            f"Build it first with: "
            f"python -m airport_mapper.polyline_to_graph --iata {iata}"
        )

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    graph = data['adjacency']
    node_types = data['node_types']
    node_pos = data.get('node_positions', {})

    # Exclusive nodes: runways, intersections, holding positions.
    exclusive_nodes = {
        n for n, t in node_types.items() if t in {'R', 'I', 'H'}
    }
    stand_nodes = {n for n, t in node_types.items() if t == 'S'}
    runway_nodes = {n for n, t in node_types.items() if t == 'R'}

    current_iata = iata

    # Invalidate compressed caches so next access rebuilds for this airport.
    _compressed_graph_cache = None
    _compressed_chains_cache = None


def _build_compressed_cache():
    global _compressed_graph_cache, _compressed_chains_cache
    weighted = build_weighted_graph(graph, node_pos)
    cg, ch = compress_graph(weighted, node_types, return_chains=True)
    _compressed_graph_cache = cg
    _compressed_chains_cache = ch


def get_compressed_graph():
    'Return the haversine-weighted, intersection-compressed graph (cached).'
    if _compressed_graph_cache is None:
        _build_compressed_cache()
    return _compressed_graph_cache


def get_compressed_chains():
    'Return the {(u, v): [intermediate raw nodes]} mapping (cached).'
    if _compressed_chains_cache is None:
        _build_compressed_cache()
    return _compressed_chains_cache


def draw_graph(adjacency, pos, node_types=None, label_nodes=False):
    # faint edges
    for a, nbrs in adjacency.items():
        ax, ay = pos[a]
        for b in nbrs:
            bx, by = pos[b]
            plt.plot([ax, bx], [ay, by], linewidth=0.2, alpha=0.06)

    # all nodes tiny
    xs = [pos[n][0] for n in adjacency]
    ys = [pos[n][1] for n in adjacency]
    plt.scatter(xs, ys, s=1, alpha=0.25)

    if node_types:
        S = [n for n, t in node_types.items() if t == "S" and n in pos]
        R = [n for n, t in node_types.items() if t == "R" and n in pos]

        if S:
            plt.scatter(
                [pos[n][0] for n in S], [pos[n][1] for n in S], s=12, marker="s"
            )
        if R:
            plt.scatter(
                [pos[n][0] for n in R], [pos[n][1] for n in R], s=18, marker="^"
            )

        if label_nodes:
            # label only a few
            for n in R[:30] + S[:30]:
                x, y = pos[n]
                plt.text(x, y, n, fontsize=6)

    plt.gca().set_aspect("equal", adjustable="box")


def plot_route(path, node_pos, color, label=None, lw=2.5, offset_index=0, total=1):
    xs, ys = [], []

    for n in path:
        if n == "AIRBORNE":
            break
        if n not in node_pos:
            continue
        x, y = node_pos[n]
        xs.append(x)
        ys.append(y)

    if not xs:
        return

    # when multiple routes overlap, offset them perpendicular to their
    # general direction so each path is visible.
    if total and total > 1:
        dx = xs[-1] - xs[0]
        dy = ys[-1] - ys[0]
        length = math.hypot(dx, dy) or 1.0
        # unit perpendicular vector
        px, py = -dy / length, dx / length

        # scale offset relative to plot extent so it looks reasonable
        all_x = [p[0] for p in node_pos.values()]
        all_y = [p[1] for p in node_pos.values()]
        xrange = max(all_x) - min(all_x) if all_x else 1.0
        yrange = max(all_y) - min(all_y) if all_y else 1.0
        scale = max(xrange, yrange)

        mid = (total - 1) / 2.0
        step = 0.002 * scale
        offset = (offset_index - mid) * step

        xs = [x + px * offset for x in xs]
        ys = [y + py * offset for y in ys]

    plt.plot(xs, ys, color=color, linewidth=lw, label=label, zorder=10)


def build_weighted_graph(adjacency, node_pos):
    weighted = {}

    for a, nbrs in adjacency.items():
        weighted[a] = {}
        ax, ay = node_pos[a]

        for b in nbrs:
            bx, by = node_pos[b]
            d = haversine_m((ax, ay), (bx, by))
            weighted[a][b] = d

    return weighted


def compress_graph(graph_w, node_types, return_chains=False):
    '''Collapse chains of degree-2 intersection nodes into single edges.

    If return_chains is True, also returns a dict mapping (u, v) -> the
    sequence of intermediate raw nodes between u and v. The mapping is
    symmetric: chains[(u, v)] is the reverse of chains[(v, u)].
    '''
    def is_compressible(n):
        return node_types.get(n) == "I" and len(graph_w[n]) == 2

    new_graph = {}
    chains = {}
    visited = set()

    for n in graph_w:
        if n in visited:
            continue

        if is_compressible(n):
            continue

        new_graph.setdefault(n, {})

        for nbr in graph_w[n]:
            if (n, nbr) in visited or (nbr, n) in visited:
                continue

            path_len = graph_w[n][nbr]
            chain = []  # intermediate raw nodes between n and the chain end
            prev = n
            cur = nbr

            # walk the chain, haha
            while is_compressible(cur):
                visited.add((prev, cur))
                visited.add((cur, prev))
                chain.append(cur)

                a, b = list(graph_w[cur].keys())

                if a == prev:
                    next_node = b
                else:
                    next_node = a

                path_len += graph_w[cur][next_node]
                prev, cur = cur, next_node

            # cur is now not compressible
            new_graph.setdefault(cur, {})
            new_graph[n][cur] = path_len
            new_graph[cur][n] = path_len

            chains[(n, cur)] = chain
            chains[(cur, n)] = list(reversed(chain))

            visited.add((n, nbr))
            visited.add((nbr, n))

    if return_chains:
        return new_graph, chains
    return new_graph


def connected_components(adjacency=None):
    '''Return a list of node sets, one per connected component.

    Defaults to the currently loaded airport's raw graph.
    '''
    if adjacency is None:
        adjacency = graph
    seen = set()
    components = []
    for start in adjacency:
        if start in seen:
            continue
        comp = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in comp:
                continue
            comp.add(n)
            for nbr in adjacency[n]:
                if nbr not in comp:
                    stack.append(nbr)
        seen |= comp
        components.append(comp)
    return components


def operational_component():
    '''Return the largest connected component that contains BOTH stands and
    runways.

    Useful for filtering random scenario generation when an airport's OSM
    data has disconnected satellite stands or apron islands.
    '''
    components = connected_components()
    best = None
    best_score = -1
    for comp in components:
        s = len(comp & stand_nodes)
        r = len(comp & runway_nodes)
        # Score by stands * runways so a component with both wins.
        score = s * r
        if score > best_score:
            best_score = score
            best = comp
    if best is None or best_score == 0:
        # Degenerate: no component has both. Return the largest one anyway
        # so callers get something usable.
        return max(components, key=len) if components else set()
    return best


def airport_summary():
    'Print a structural summary of the currently loaded airport.'
    components = connected_components()
    components.sort(key=len, reverse=True)
    print(f'== {current_iata} ==')
    print(f'total nodes: {len(graph)}')
    print(f'edges: {sum(len(v) for v in graph.values()) // 2}')
    print(f'connected components: {len(components)}')
    print(f'stands: {len(stand_nodes)}, runways: {len(runway_nodes)}, '
          f'holding: {sum(1 for t in node_types.values() if t == "H")}')

    main = operational_component()
    main_s = len(main & stand_nodes)
    main_r = len(main & runway_nodes)
    print(f'\noperational component: {len(main)} nodes, '
          f'{main_s}/{len(stand_nodes)} stands, '
          f'{main_r}/{len(runway_nodes)} runways')

    print('\ntop components by size:')
    for i, comp in enumerate(components[:8]):
        s = len(comp & stand_nodes)
        r = len(comp & runway_nodes)
        flag = ' (operational)' if comp is main else ''
        print(f'  [{i}] {len(comp):>5} nodes, {s:>3} stands, {r:>3} runways{flag}')


def expand_compressed_path(compressed_path, chains):
    '''Expand a path on the compressed graph back to the full raw path.

    For each consecutive pair (u, v) in the compressed path, splices in the
    intermediate chain nodes from chains[(u, v)] so the resulting path is
    edge-by-edge adjacent in the raw graph.
    '''
    if compressed_path is None:
        return None
    if len(compressed_path) < 2:
        return list(compressed_path)

    raw = [compressed_path[0]]
    for u, v in zip(compressed_path, compressed_path[1:]):
        chain = chains.get((u, v), [])
        raw.extend(chain)
        raw.append(v)
    return raw


# Bind the default airport at module load. Existing imports of graph,
# node_types, node_pos etc. work unchanged.
load_airport(DEFAULT_IATA)
