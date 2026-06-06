import json
import urllib.request
import re
import os

target_files = ["Neon.json", "Oxygen.json", "2018-09.json", "2026-03.json"]
target_features = ["CDT", "JDT", "PDE", "GEF", "EMF"]
json_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models\releases\dados-features"

results = {}

def check_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        
        # Look for github commit links
        commits = re.findall(r'href=[\'"]?(https://github\.com/[^\'"]+/commit/[0-9a-fA-F]+)', html)
        if commits:
            return "SUCCESS", f"Found GitHub commit links in HTML: {commits[0]}"
            
        # Look for ci-and-git-info.txt link
        if "ci-and-git-info.txt" in html:
            return "SUCCESS", "Found ci-and-git-info.txt link in HTML"
            
        return "FAILED", "No github commit or ci-and-git-info link found in HTML"
    except Exception as e:
        return "FAILED", f"Error fetching HTML: {str(e)}"

for file in target_files:
    filepath = os.path.join(json_dir, file)
    if not os.path.exists(filepath):
        continue
    results[file] = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for feat in target_features:
            feature_data = data.get("features", {}).get(feat)
            if feature_data:
                url = feature_data.get("repository_url")
                if not url:
                    results[file][feat] = ("FAILED", "No repository_url in JSON")
                else:
                    if not url.endswith('/'): url += '/'
                    status, msg = check_url(url)
                    # If failed, try ci-and-git-info.txt directly
                    if status == "FAILED" and "Error fetching HTML" not in msg:
                        try:
                            ci_url = url + "ci-and-git-info.txt"
                            req = urllib.request.Request(ci_url, headers={'User-Agent': 'Mozilla/5.0'})
                            content = urllib.request.urlopen(req, timeout=3).read().decode('utf-8')
                            match = re.search(r'\*\s+([0-9a-fA-F]{7,40})\b', content)
                            if match:
                                status, msg = "SUCCESS", f"Found commit via direct ci-and-git-info.txt fetch: {match.group(1)}"
                        except:
                            pass
                    results[file][feat] = (status, msg)

print("=== RELATORIO INICIAL DE MAPEAMENTO ===")
for file, feats in results.items():
    print(f"\n--- {file} ---")
    for feat, (status, msg) in feats.items():
        print(f"[{status}] {feat}: {msg}")
