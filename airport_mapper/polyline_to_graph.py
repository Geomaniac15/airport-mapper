import json
import os

from airport_mapper.coord_graph import build_graph_from_polylines

FILE = 'jfk_graph.json'

def build_graph(overpass_json, decimals=4, aeroway_types=None):
    '''
    extract polylines from overpass JSON data
    '''
    if aeroway_types is not None:
        aeroway_types = set(aeroway_types)
    
    polylines = []

    for e in overpass_json.get('elements',[]):
        if e.get('type') != 'way':
            continue

        tags = e.get('tags', {}) or {}
        aeroway = tags.get('aeroway')
        if aeroway is None:
            continue
        if aeroway_types is not None and aeroway not in aeroway_types:
            continue

        geom = e.get('geometry')
        if not geom:
            continue

        coords = [(pt["lon"], pt["lat"]) for pt in geom if "lon" in pt and "lat" in pt]
        polylines.append(coords)
    
    return polylines

with open(os.path.join(os.path.dirname(__file__), 'overpass_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

polylines = build_graph(
    data,
    decimals=5,
    aeroway_types={'taxiway', 'taxilane', 'runway', 'apron'},
)

graph, node_pos = build_graph_from_polylines(polylines)

with open(FILE, 'w', encoding='utf-8') as f:
    json.dump(graph, f, indent=2)

#print('graph:', graph)
# print('node positions:', node_pos)

# n = next(iter(graph))
# print(f'sample node: {n}, degree {len(graph[n])}')