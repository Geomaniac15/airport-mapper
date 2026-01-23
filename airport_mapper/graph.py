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

def draw_graph(graph):
    G = nx.Graph()

    for node, neighbours in graph.items():
        for neighbour in neighbours:
            G.add_edge(node, neighbour)

    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, seed=42)
    nx.draw(
        G, 
        pos, 
        with_labels=True, 
        node_size=2000, 
        font_size=10)
    plt.show()