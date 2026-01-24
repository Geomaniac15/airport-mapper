import requests
import json

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def overpass(query: str) -> dict:
    r = requests.post(OVERPASS_URL, data={'data': query}, timeout=600)
    if not r.ok:
        print('Overpass query failed:', r.text[:2000])
    r.raise_for_status()
    return r.json()

def get_area_id_for_iata(iata: str) -> int:
    query = f"""
    [out:json][timeout:25];
    (
      rel["aeroway"="aerodrome"]["iata"="{iata}"];
      way["aeroway"="aerodrome"]["iata"="{iata}"];
      node["aeroway"="aerodrome"]["iata"="{iata}"];
    );
    out ids;
    """
    print('Executing query:', query)  # Log the query being sent
    data = overpass(query)
    elements = data.get('elements', [])
    if not elements:
        print('No aerodrome elements found for IATA code:', iata)  # Log the IATA code
        raise ValueError(f'No aerodrome elements found for IATA code {iata}')
    elem = elements[0]
    elem_id = elem['id']
    elem_type = elem['type']
    print(f'Element type: {elem_type}, ID: {elem_id}')
    if elem_type == 'relation':
        area_id = 3600000000 + elem_id
    elif elem_type == 'way':
        area_id = 2400000000 + elem_id
    elif elem_type == 'node':
        area_id = 3600000000 + elem_id
    else:
        raise ValueError(f'Unexpected element type: {elem_type}')
    return area_id

area_id = get_area_id_for_iata('LAX')
print(f'Area ID: {area_id}')

query = f"""
[out:json][timeout:300];

way["aeroway"](area:{area_id});

out tags;
"""

try:
    data = overpass(query)
    print(len(data['elements']))
except Exception as e:
    print(f'Error in big query: {e}')
