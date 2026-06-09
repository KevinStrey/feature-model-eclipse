import json
import urllib.request
import re
import os
import glob
import sys

# Path to the directory containing JSON files
json_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models\releases\dados-features"
json_files = glob.glob(os.path.join(json_dir, "*.json"))

mapped = []
unmapped = []

def get_ci_info(feature_name, feature_data, release_name):
    repo_url = feature_data.get("repository_url")
    if not repo_url:
        return (release_name, feature_name, feature_data.get('version'), False, "No repository_url")

    if not repo_url.endswith('/'):
        repo_url += '/'
    
    ci_url = repo_url + "ci-and-git-info.txt"
    try:
        req = urllib.request.Request(ci_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            content = response.read().decode('utf-8')
            
            # Extract commit hash: Look for "* <hash> ["
            match = re.search(r'\*\s+([0-9a-fA-F]{7,40})\b', content)
            if match:
                commit_hash = match.group(1)
                return (release_name, feature_name, feature_data.get('version'), True, ci_url, commit_hash)
            else:
                return (release_name, feature_name, feature_data.get('version'), False, f"Found file but no commit hash in {ci_url}")
    except urllib.error.URLError as e:
        return (release_name, feature_name, feature_data.get('version'), False, f"HTTP Error/Not Found for {ci_url}")
    except Exception as e:
        return (release_name, feature_name, feature_data.get('version'), False, f"Error: {str(e)}")

print("Processando arquivos JSON...", flush=True)

for filepath in json_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        release = data.get('release', os.path.basename(filepath))
        features = data.get('features', {})
        for feature_name, feature_data in features.items():
            print(f"[{release}] Verificando {feature_name}...", end=" ", flush=True)
            result = get_ci_info(feature_name, feature_data, release)
            if result[3]: # Mapped = True
                mapped.append(result)
                print(f"SUCESSO ({result[5]})", flush=True)
            else:
                unmapped.append(result)
                print(f"FALHOU", flush=True)

print("\n" + "="*50)
print(f"MAPPED FEATURES ({len(mapped)}):")
for m in mapped:
    print(f"[{m[0]}] {m[1]} ({m[2]}) -> Commit: {m[5]} (Source: {m[4]})")

output_file = r"c:\Users\Kevin Strey\Desktop\Feature-models\mapping_results.txt"
with open(output_file, "w", encoding='utf-8') as f:
    f.write(f"MAPPED FEATURES ({len(mapped)}):\n")
    for m in mapped:
        f.write(f"[{m[0]}] {m[1]} ({m[2]}) -> Commit: {m[5]} (Source: {m[4]})\n")
    f.write(f"\nUNMAPPED FEATURES ({len(unmapped)}):\n")
    for u in unmapped:
        f.write(f"[{u[0]}] {u[1]} ({u[2]}) -> {u[4]}\n")

print(f"\nResultados salvos em {output_file}", flush=True)
