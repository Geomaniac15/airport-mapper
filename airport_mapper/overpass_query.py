import json

import requests

FILE = "airport_mapper/overpass_data.json"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def overpass(query: str) -> dict:
    r = requests.post(OVERPASS_URL, data={"data": query}, timeout=600)
    if not r.ok:
        print("Overpass query failed:", r.text[:2000])
    r.raise_for_status()
    return r.json()


def get_airport_aeroway_features_by_iata(iata: str) -> dict:
    query = f"""
    [out:json][timeout:300];

    // Prefer relation/way airport boundary if it exists
    (
      rel["aeroway"="aerodrome"]["iata"="{iata}"];
      way["aeroway"="aerodrome"]["iata"="{iata}"];
    )->.airport;

    // If we found a boundary-ish object, turn it into an area and query inside it
    (
      .airport;
      node["aeroway"="aerodrome"]["iata"="{iata}"];
    )->.any;

    // Try area route first
    .airport map_to_area -> .a;

    (
      way["aeroway"](area.a);
      node["aeroway"](area.a);
      rel["aeroway"](area.a);
    )->.inside;

    // If area query returns nothing, fall back to around() using aerodrome node location
    // Overpass can't do if/else, so we do this and merge results client-side.
    node["aeroway"="aerodrome"]["iata"="{iata}"]->.p;
    (
      way["aeroway"](around.p:10000);
      node["aeroway"](around.p:10000);
      rel["aeroway"](around.p:10000);
    )->.near;

    (.inside; .near;);
    out body geom;
    """
    return overpass(query)


data = get_airport_aeroway_features_by_iata("JFK")
# print("elements:", len(data.get("elements", [])))
# print(data)

with open(FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

ways = [e for e in data["elements"] if e.get("type") == "way" and "geometry" in e]

polylines = []
for way in ways:
    coords = [(pt["lon"], pt["lat"]) for pt in way["geometry"]]
    tags = way.get("tags", {})
    polylines.append(
        {
            "id": way["id"],
            "aeroway": tags.get("aeroway"),
            "ref": tags.get("ref"),
            "coords": coords,
        }
    )

print(f"ways with geometry: {len(polylines)}")
print("sample way:", polylines[0] if polylines else None)
