import json
from collections import Counter

with open('airport_mapper/overpass_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

c = Counter()
for e in data.get('elements', []):
    if e.get('type') == 'node':
        aeroway = (e.get('tags') or {}).get('aeroway')
        if aeroway:
            c[aeroway] += 1

print('node aeroway tag  counts:')
for k, v in c.most_common():
    print(k, v)