import json
import math
import os

import matplotlib.pyplot as plt

from airport_mapper.polyline_to_graph import haversine_m

# Load JFK graph from JSON
HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "jfk_graph_labeled.json"), "r", encoding="utf-8") as f:
    _jfk_data = json.load(f)

graph = _jfk_data["adjacency"]
node_types = _jfk_data["node_types"]
node_pos = _jfk_data.get("node_positions", {})

# Exclusive nodes are runways (R) and intersections (I) - only one aircraft at a time
exclusive_nodes = {
    node for node, ntype in node_types.items() if ntype in {"R", "I", "H"}
}

# Non-exclusive nodes are stands (S) - multiple aircraft can wait at stands
stand_nodes = {node for node, ntype in node_types.items() if ntype == "S"}
runway_nodes = {node for node, ntype in node_types.items() if ntype == "R"}

# Lazy cache of the compressed weighted graph used for path planning.
# Built on first access so module import stays cheap.
_compressed_graph_cache = None


def get_compressed_graph():
    'Return the haversine-weighted, intersection-compressed graph (cached).'
    global _compressed_graph_cache
    if _compressed_graph_cache is None:
        weighted = build_weighted_graph(graph, node_pos)
        _compressed_graph_cache = compress_graph(weighted, node_types)
    return _compressed_graph_cache


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


def compress_graph(graph_w, node_types):
    def is_compressible(n):
        return node_types.get(n) == "I" and len(graph_w[n]) == 2

    new_graph = {}
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
            prev = n
            cur = nbr

            # walk the chain, haha
            while is_compressible(cur):
                visited.add((prev, cur))
                visited.add((cur, prev))

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

            visited.add((n, nbr))
            visited.add((nbr, n))

    return new_graph
