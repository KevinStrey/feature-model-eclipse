import json
from pathlib import Path

files = [
    '2018-09.json', '2020-03.json', '2022-03.json', '2023-09.json', 
    '2024-09.json', '2025-09.json', 'JunoSR1.json', 'Neon.2.json', 
    'Oxygen.3.json', 'z20140805-2300.json'
]

base_path = Path(r'c:\Users\Kevin Strey\Desktop\Feature-models\3-Mapeamento_features_simrel\simrel_mapper\output')

results = []
for fname in files:
    fpath = base_path / fname
    if not fpath.exists(): continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for feature, info in data.get('mappings', {}).items():
        if info.get('heuristic_id') in ['H0', 'H5']:
            results.append({
                'release': data.get('release'),
                'feature': feature,
                'version': info.get('version'),
                'heuristic': info.get('heuristic_description'),
                'matched': info.get('matched_value'),
                'commit': info.get('commit')[:8] if info.get('commit') else None
            })

for r in results:
    print(f"Release: {r['release']:<10} | Feature: {r['feature']:<15} | Version: {r['version']:<25} | Heuristica: {r['heuristic']:<28} | Match: {r['matched']}")
