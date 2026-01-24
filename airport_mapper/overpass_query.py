import requests
import json

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def overpass(query: str) -> dict:
    r = requests.post(OVERPASS_URL, data={'data': query}, timeout=120)
    r.raise_for_status()
    return r.json()

query = f"""
[out:json][timeout:60];
{{geocodeArea:London Gatwick Airport}}->.a;

(
  way["aeroway"="runway"](area.a);
  way["aeroway"="taxiway"](area.a);
  way["aeroway"="taxilane"](area.a);

  node["aeroway"="parking_position"](area.a);
  node["aeroway"="gate"](area.a);
  node["aeroway"="holding_position"](area.a);
);

out tags geom;
"""

data = overpass(query)
print(len(data['elements']))
