import argparse
import json
import math
import os
import sys

from airport_mapper.coord_graph import build_graph_from_polylines

HERE = os.path.dirname(__file__)
AIRPORTS_DIR = os.path.join(HERE, 'airports')

EDGE_AEROWAYS = {"taxiway", "taxilane", "runway", "apron"}
STAND_AEROWAYS = {"gate", "parking_position", "stand"}


def round_func(lon, lat, decimals):
    return (round(lon, decimals), round(lat, decimals))


def extract_stand_points(overpass_json, decimals=5):
    # extract stand node points from overpass JSON data

    pts = []

    for e in overpass_json.get("elements", []):
        if e.get("type") != "node":
            continue

        tags = e.get("tags", {}) or {}
        aeroway = tags.get("aeroway")
        if aeroway in {"gate", "parking_position", "stand"}:
            lon = e.get("lon")
            lat = e.get("lat")
            if lon is not None and lat is not None:
                pts.append((lon, lat))

    return pts


def extract_holding_positions(overpass_json):
    pts = []

    for e in overpass_json.get("elements", []):
        if e.get("type") != "node":
            continue

        tags = e.get("tags", {}) or {}
        if tags.get("aeroway") == "holding_position":
            lon = e.get("lon")
            lat = e.get("lat")
            if lon is not None and lat is not None:
                pts.append((lon, lat))

    return pts


def haversine_m(a, b):
    R = 6371000.0
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    x = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(x))


def snap_points_to_graph(points, node_pos, candidates=None, max_dist_m=40):
    if candidates is None:
        nodes = list(node_pos.items())
    else:
        nodes = [(n, node_pos[n]) for n in candidates]

    snapped = {}
    for p in points:
        best_node = None
        best_d = float("inf")
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
            node_type[n] = "S"
            continue

        incident_types = set()
        for nbr, types in nbrs.items():
            incident_types |= set(types)

        has_runway = "runway" in incident_types
        has_taxi = bool(incident_types & {"taxiway", "taxilane"})

        if has_runway and has_taxi:
            node_type[n] = "R"
        else:
            node_type[n] = "I"

    return node_type


def graph_to_adjacency(graph):
    return {n: sorted(nbrs.keys()) for n, nbrs in graph.items()}


def extract_polylines(overpass_json, aeroway_types=None, decimals=5):
    if aeroway_types is not None:
        aeroway_types = set(aeroway_types)

    tagged = []
    for e in overpass_json.get("elements", []):
        if e.get("type") != "way":
            continue

        tags = e.get("tags", {}) or {}
        aeroway = tags.get("aeroway")
        if not aeroway:
            continue
        if aeroway_types is not None and aeroway not in aeroway_types:
            continue

        geom = e.get("geometry")
        if not geom:
            continue

        coords = [(pt["lon"], pt["lat"]) for pt in geom if "lon" in pt and "lat" in pt]
        if len(coords) < 2:
            continue

        tagged.append(
            {
                "id": e.get("id"),
                "ref": tags.get("ref"),
                "aeroway": aeroway,
                "coords": coords,
            }
        )

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

def _connected_components_typed(graph_typed):
    'Connected components of a typed graph (adjacency: dict[node, dict[node, set]]).'
    seen = set()
    comps = []
    for start in graph_typed:
        if start in seen:
            continue
        comp = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in comp:
                continue
            comp.add(n)
            for nbr in graph_typed[n]:
                if nbr not in comp:
                    stack.append(nbr)
        seen |= comp
        comps.append(comp)
    return comps


def bridge_isolated_components(graph_typed, node_pos, node_type,
                               max_dist_m=400, verbose=False):
    '''Connect components containing operationally relevant nodes (stands,
    runways, holding points) to the main component via the shortest possible
    bridge edge.

    OSM apron polygons are often missing the small connector taxilane that
    physically links them to the main taxiway network, leaving stands as
    floating islands. This pass closes those gaps with synthetic edges
    tagged 'bridge'. The number of bridges added is returned.
    '''
    OPERATIONAL = {'S', 'R', 'H'}

    components = _connected_components_typed(graph_typed)
    components.sort(key=len, reverse=True)
    if not components:
        return 0

    # Main component is the largest one containing stands+runways. If no
    # component contains both, fall back to the largest one.
    def has_both(comp):
        s = any(node_type.get(n) == 'S' for n in comp)
        r = any(node_type.get(n) == 'R' for n in comp)
        return s and r

    main = next((c for c in components if has_both(c)), components[0])

    bridges = 0
    for comp in components:
        if comp is main:
            continue
        # Skip components without any operationally relevant nodes.
        relevant = [n for n in comp if node_type.get(n) in OPERATIONAL]
        if not relevant:
            continue

        # Find the closest pair (a in comp, b in main).
        # Restrict to candidates within a bounding box for speed.
        best = None
        best_d = float('inf')
        for a in relevant:
            ax, ay = node_pos[a]
            for b in main:
                bx, by = node_pos[b]
                # cheap pre-filter on bbox
                if abs(ax - bx) > 0.01 or abs(ay - by) > 0.01:
                    continue
                d = haversine_m((ax, ay), (bx, by))
                if d < best_d:
                    best_d = d
                    best = (a, b)
        if best is None or best_d > max_dist_m:
            if verbose:
                print(
                    f'  could not bridge component of {len(comp)} nodes '
                    f'({len(relevant)} relevant); nearest pair {best_d:.0f}m '
                    f'> {max_dist_m}m'
                )
            continue

        a, b = best
        # Add a synthetic edge in the typed graph.
        graph_typed[a].setdefault(b, set()).add('bridge')
        graph_typed[b].setdefault(a, set()).add('bridge')
        main = main | comp
        bridges += 1
        if verbose:
            print(
                f'  bridge: {a} <-> {b} ({best_d:.0f}m), merged '
                f'{len(comp)} nodes into main'
            )

    return bridges


def build_airport_graph(iata, verbose=True, fetch_if_missing=True):
    '''Rebuild airports/<IATA>.json from airports/<IATA>.overpass.json.

    If the Overpass JSON is missing and fetch_if_missing is True, fetch it
    via the Overpass API first. Only intended to be called when the
    underlying OSM data changes (or for a new airport).
    '''
    iata = iata.upper()
    os.makedirs(AIRPORTS_DIR, exist_ok=True)
    overpass_path = os.path.join(AIRPORTS_DIR, f'{iata}.overpass.json')
    out_path = os.path.join(AIRPORTS_DIR, f'{iata}.json')

    if not os.path.exists(overpass_path):
        if not fetch_if_missing:
            raise FileNotFoundError(
                f'No Overpass cache for {iata} at {overpass_path}'
            )
        if verbose:
            print(f'fetching Overpass data for {iata}...')
        from airport_mapper.overpass_query import fetch_airport
        fetch_airport(iata, save_to=overpass_path, verbose=verbose)

    with open(overpass_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tagged_polylines = extract_polylines(
        data,
        decimals=5,
        aeroway_types=EDGE_AEROWAYS,
    )

    stand_points = extract_stand_points(data)
    holding_pts = extract_holding_positions(data)

    graph_typed, node_pos, _key_to_node = build_graph_from_polylines(
        tagged_polylines,
        decimals=5,
    )

    node_type = label_nodes(
        graph_typed,
        node_pos,
        stand_keys=set(),
    )

    # candidate nodes: nodes with at least one taxilane-class incident edge
    candidates = []
    for n, nbrs in graph_typed.items():
        incident = set()
        for types in nbrs.values():
            incident |= set(types)
        if incident & EDGE_AEROWAYS:
            candidates.append(n)

    snapped = snap_points_to_graph(
        stand_points, node_pos, candidates=candidates, max_dist_m=50
    )
    snapped_holding_pts = snap_points_to_graph(
        holding_pts, node_pos, candidates=candidates, max_dist_m=30
    )

    for node in snapped.values():
        node_type[node] = "S"
    for node in snapped_holding_pts.values():
        node_type[node] = "H"

    bridges = bridge_isolated_components(
        graph_typed, node_pos, node_type, max_dist_m=400, verbose=verbose,
    )

    out = {
        'iata': iata,
        'adjacency': graph_to_adjacency(graph_typed),
        'node_positions': node_pos,
        'node_types': node_type,
        'bridges_added': bridges,
        'edge_types': {
            n: {nbr: sorted(types) for nbr, types in nbrs.items()}
            for n, nbrs in graph_typed.items()
        },
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    if verbose:
        counts = {}
        for t in node_type.values():
            counts[t] = counts.get(t, 0) + 1
        print(f'[{iata}] candidate nodes (taxilane-adjacent): {len(candidates)}')
        print(f'[{iata}] polylines: {len(tagged_polylines)}')
        print(f'[{iata}] nodes: {len(out["adjacency"])}')
        print(f'[{iata}] edges: {sum(len(v) for v in out["adjacency"].values()) // 2}')
        print(f'[{iata}] node type counts: {counts}')
        print(f'[{iata}] stand points (OSM): {len(stand_points)}')
        print(f'[{iata}] snapped stands: {len(snapped)}, holding pts: {len(snapped_holding_pts)}')
        print(f'[{iata}] wrote: {out_path}')

    return out


def _main(argv=None):
    parser = argparse.ArgumentParser(
        description='Build airports/<IATA>.json from Overpass data.',
    )
    parser.add_argument(
        '--iata', '-i', default='JFK',
        help='IATA airport code to (re)build (default: JFK)',
    )
    parser.add_argument(
        '--no-fetch', action='store_true',
        help='do not call Overpass; require airports/<IATA>.overpass.json on disk',
    )
    args = parser.parse_args(argv)
    build_airport_graph(args.iata, fetch_if_missing=not args.no_fetch)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
