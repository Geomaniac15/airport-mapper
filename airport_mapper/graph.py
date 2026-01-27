import networkx as nx
import matplotlib.pyplot as plt

graph = {
    # Stands
    'S1': ['I1'],
    'S2': ['I2'],
    'S3': ['I6'],

    # Intersections
    'I1': ['S1', 'I3', 'I4'],
    'I2': ['S2', 'I3', 'I5'],
    'I3': ['I1', 'I2', 'I4', 'I5'],
    'I4': ['I1', 'I3', 'I6', 'I7'],
    'I5': ['I2', 'I3', 'R2'],
    'I6': ['S3', 'I7'],
    'I7': ['I4', 'I6', 'R1'],

    # Runway Access Points
    'R1': ['I7', 'RWY'],
    'R2': ['I5', 'RWY'],

    # Runway
    'RWY': ['R1', 'R2'],
}

exclusive_nodes = {'I1','I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'R1', 'R2', 'RWY'}

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
            # label only a few, otherwise you get your black-hole again
            for n in (R[:30] + S[:30]):
                x, y = pos[n]
                plt.text(x, y, n, fontsize=6)

    plt.gca().set_aspect("equal", adjustable="box")
    plt.show()