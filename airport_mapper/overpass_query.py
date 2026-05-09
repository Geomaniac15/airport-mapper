'''Overpass API queries for airport ground features.

Functions in this module never hit the network at import time. Call
fetch_airport(iata) (or run as a script) to actually fetch.
'''

import argparse
import json
import os
import sys

import requests

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

# Public Overpass instances reject requests without a proper User-Agent
# (returns Apache 406). They also rate-limit aggressively, so identify
# yourself politely.
USER_AGENT = 'airport-mapper-sim/0.1 (https://github.com/Geomaniac15/airport-mapper)'

HERE = os.path.dirname(__file__)
AIRPORTS_DIR = os.path.join(HERE, 'airports')


def overpass(query):
    'Run an Overpass QL query and return the parsed JSON response.'
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
    }
    r = requests.post(
        OVERPASS_URL,
        data={'data': query},
        headers=headers,
        timeout=600,
    )
    if not r.ok:
        print('Overpass query failed:', r.text[:2000])
    r.raise_for_status()
    return r.json()


def get_airport_aeroway_features_by_iata(iata, radius_m=8000):
    '''Fetch all aeroway features near the airport with this IATA tag.

    Uses an around() query instead of map_to_area so airports tagged only
    as a node (rather than as a way/relation boundary) still work. radius_m
    controls how far from the airport centre to search; 8000 m comfortably
    covers even very large airports like LHR or DXB.
    '''
    query = f'''
    [out:json][timeout:300];

    // Find the airport, accepting any element type. Some airports are
    // tagged as a closed way or boundary relation; many smaller ones are
    // a single node.
    (
      node["aeroway"="aerodrome"]["iata"="{iata}"];
      way["aeroway"="aerodrome"]["iata"="{iata}"];
      rel["aeroway"="aerodrome"]["iata"="{iata}"];
    )->.airport;

    // All aeroway features within radius_m metres of any airport element.
    (
      way["aeroway"](around.airport:{radius_m});
      node["aeroway"](around.airport:{radius_m});
    );
    out body geom;
    '''
    return overpass(query)


def fetch_airport(iata, save_to=None, verbose=True):
    '''Fetch aeroway data for `iata` and save to airports/<IATA>.overpass.json.

    Returns the parsed JSON. If save_to is provided, writes there instead of
    the default airports/ location.
    '''
    iata = iata.upper()
    if save_to is None:
        os.makedirs(AIRPORTS_DIR, exist_ok=True)
        save_to = os.path.join(AIRPORTS_DIR, f'{iata}.overpass.json')

    data = get_airport_aeroway_features_by_iata(iata)

    with open(save_to, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    if verbose:
        elems = data.get('elements', [])
        ways = sum(1 for e in elems if e.get('type') == 'way')
        nodes = sum(1 for e in elems if e.get('type') == 'node')
        print(
            f'[{iata}] fetched {len(elems)} elements '
            f'({ways} ways, {nodes} nodes), saved to {save_to}'
        )

    return data


def _main(argv=None):
    parser = argparse.ArgumentParser(
        description='Fetch airport aeroway data from Overpass.',
    )
    parser.add_argument('iata', help='IATA airport code (e.g. LHR)')
    args = parser.parse_args(argv)
    fetch_airport(args.iata)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
