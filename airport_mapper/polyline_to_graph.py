import json
import os
import math

from airport_mapper.coord_graph import build_graph_from_polylines
from airport_mapper.graph import draw_graph

FILE = 'airport_mapper/jfk_graph_labeled.json'

EDGE_AEROWAYS = {'taxiway', 'taxilane', 'runway'}
STAND_AEROWAYS = {'gate', 'parking_position', 'stand'}

def round_func(lon, lat, decimals):
    return (round(lon, decimals), round(lat, decimals))

def extract_stand_keys(overpass_json, decimals=5):
    # extract stand node keys from overpass JSON data

    stand_keys = set()

    for e in overpass_json.get('elements',[]):
        if e.get('type') != 'node':
            continue

        tags = e.get('tags', {}) or {}
        aeroway = tags.get('aeroway')
        if tags.get('aeroway') in {'gate', 'parking_position', 'stand'}:
            lon = e.get('lon')
            lat = e.get('lat')
            if lon is not None and lat is not None:
                stand_keys.add(round_func(lon, lat, decimals))
    
    return stand_keys

def haversine_m(a, b):
    R = 6371000.0
    lon1, lat1 = map(math.randians, a)
    lon2, lat2 = map(math.randians, b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    x = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(x))

def snap_points_to_graph(points, node_pos, max_dist_m=40):
    nodes = list(node_pos.items())
    snapped = {}
    for p in points:
        best_node = None
        best_d = float('inf')
        for node_id, coord in nodes:
            d = haversine_m(p, coord)
            if d < best_d:
                best_d = d
                best_node = node_id
        
        if best_node is not None and best_d <= max_dist_m:
            snapped[p] = best_node
    
    return snapped

def label_nodes(graph, node_pos, stand_keys):
    node_type = {}

    for n, nbrs in graph.items():
        pos_key = node_pos.get(n)
        if pos_key in stand_keys:
            node_type[n] = 'S'
            continue

        incident_types = set()
        for nbr, types in nbrs.items():
            incident_types |= set(types)
        
        has_runway = 'runway' in incident_types
        has_taxi = bool(incident_types & {'taxiway', 'taxilane'})

        if has_runway and has_taxi:
            node_type[n] = 'R'
        else:
            node_type[n] = 'I'
        
    return node_type

def graph_to_adjacency(graph):
    return {n: sorted(nbrs.keys()) for n, nbrs in graph.items()}

def extract_polylines(overpass_json, aeroway_types=None, decimals=5):
    if aeroway_types is not None:
        aeroway_types = set(aeroway_types)
    
    tagged = []
    for e in overpass_json.get('elements',[]):
        if e.get('type') != 'way':
            continue

        tags = e.get('tags', {}) or {}
        aeroway = tags.get('aeroway')
        if not aeroway:
            continue
        if aeroway_types is not None and aeroway not in aeroway_types:
            continue

        geom = e.get('geometry')
        if not geom:
            continue

        coords = [(pt['lon'], pt['lat']) for pt in geom if 'lon' in pt and 'lat' in pt]
        if len(coords) < 2:
            continue

        tagged.append({
            'id': e.get('id'),
            'ref': tags.get('ref'),
            'aeroway': aeroway,
            'coords': coords,
        })
    
    return tagged

# def build_graph(overpass_json, decimals=4, aeroway_types=None):
#     '''
#     extract polylines from overpass JSON data
#     '''
#     if aeroway_types is not None:
#         aeroway_types = set(aeroway_types)
    
#     polylines = []

#     for e in overpass_json.get('elements',[]):
#         if e.get('type') != 'way':
#             continue

#         tags = e.get('tags', {}) or {}
#         aeroway = tags.get('aeroway')
#         if aeroway is None:
#             continue
#         if aeroway_types is not None and aeroway not in aeroway_types:
#             continue

#         geom = e.get('geometry')
#         if not geom:
#             continue

#         coords = [(pt["lon"], pt["lat"]) for pt in geom if "lon" in pt and "lat" in pt]
#         polylines.append(coords)
    
#     return polylines

# with open(os.path.join(os.path.dirname(__file__), 'overpass_data.json'), 'r', encoding='utf-8') as f:
#     data = json.load(f)

# polylines = build_graph(
#     data,
#     decimals=5,
#     aeroway_types={'taxiway', 'taxilane', 'runway', 'apron'},
# )

# print('Number of polylines:', len(polylines))
# # print('Polyline lengths:', [len(p) for p in polylines])

# graph, node_pos = build_graph_from_polylines(polylines, decimals=5)

# print('Number of nodes:', len(graph))
# print('Total edges:', sum(len(v) for v in graph.values()) // 2)
# print('Degrees:', sorted(set(len(v) for v in graph.values())))
# print('\n')

# print('Top 10 nodes by degree:')
# top10 = sorted(graph.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]

# for node, neighbors in top10:
#     print(f'Node {node} (degree {len(neighbors)}): neighbors {neighbors}')

# with open(FILE, 'w', encoding='utf-8') as f:
#     json.dump(graph, f, indent=2)

# #print('graph:', graph)
# # print('node positions:', node_pos)

# # n = next(iter(graph))
# # print(f'sample node: {n}, degree {len(graph[n])}')

HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, 'overpass_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

tagged_polylines = extract_polylines(
    data,
    decimals=5,
    aeroway_types=EDGE_AEROWAYS,
)

stand_keys = extract_stand_keys(
    data,
    decimals=5,
)

graph_typed, node_pos, key_to_node = build_graph_from_polylines(
    tagged_polylines,
    decimals=5,
)

node_type = label_nodes(
    graph_typed,
    node_pos,
    stand_keys=stand_keys,
)

out = {
    'adjacency': graph_to_adjacency(graph_typed),
    'node_positions': node_pos,
    'node_types': node_type,
    'edge_types': {
        n: {nbr: sorted(types) for nbr, types in nbrs.items()}
        for n, nbrs in graph_typed.items()
    },
}


print('polylines:', len(tagged_polylines))
print('nodes:', len(out['adjacency']))
print('edges:', sum(len(v) for v in out['adjacency'].values()) // 2)

counts = {'R':0,
          'S':0,
          'I':0}
for t in node_type.values():
    counts[t] = counts.get(t, 0) + 1
print('node type counts:', counts)

with open(FILE, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)

print('wrote to:', FILE)

draw_graph(out['adjacency'], pos=out['node_positions'], node_types=out['node_types'])

# print('\n')
# print(out['adjacency'], pos=out['node_positions'], node_types=out['node_types'])
# print('\n')