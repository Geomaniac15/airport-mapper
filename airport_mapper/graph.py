import networkx as nx
import matplotlib.pyplot as plt
import json
import os

# Load JFK graph from JSON
HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, 'jfk_graph_labeled.json'), 'r', encoding='utf-8') as f:
    _jfk_data = json.load(f)

graph = _jfk_data['adjacency']
node_types = _jfk_data['node_types']

# Exclusive nodes are runways (R) and intersections (I) - only one aircraft at a time
exclusive_nodes = {node for node, ntype in node_types.items() if ntype in {'R', 'I'}}

# Non-exclusive nodes are stands (S) - multiple aircraft can wait at stands
stand_nodes = {node for node, ntype in node_types.items() if ntype == 'S'}
runway_nodes = {node for node, ntype in node_types.items() if ntype == 'R'}

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
            plt.scatter([pos[n][0] for n in S], [pos[n][1] for n in S], s=12, marker="s")
        if R:
            plt.scatter([pos[n][0] for n in R], [pos[n][1] for n in R], s=18, marker="^")

        if label_nodes:
            # label only a few
            for n in (R[:30] + S[:30]):
                x, y = pos[n]
                plt.text(x, y, n, fontsize=6)

    plt.gca().set_aspect("equal", adjustable="box")

def plot_route(path, node_pos, color='red', lw=1):
    xs, ys = [], []

    for n in path:
        if n == 'AIRBORNE':
            break
        if n not in node_pos:
            continue
        x, y = node_pos[n]
        xs.append(x)
        ys.append(y)
    
    plt.plot(xs, ys, color=color, linewidth=lw, zorder=10)