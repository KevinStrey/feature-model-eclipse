import json
import os
import subprocess
import re
import datetime

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, "releases", "dados-features")
out_dir = os.path.join(base_dir, "releases", "mappings")

os.makedirs(out_dir, exist_ok=True)

# 17 Repositories mapped
repo_map = {
    "JDT": ["eclipse.jdt.core"],
    "PDE": ["eclipse.pde"],
    "CDT": ["cdt"],
    "GEF": ["gef-classic", "gef"],
    "EMF": ["org.eclipse.emf"],
    "BIRT": ["birt"],
    "DATATOOLS": ["datatools"],
    "ECLIPSELINK": ["eclipselink"],
    "EGIT": ["egit"],
    "GMF": ["gmf-runtime"],
    "MYLYN": ["org.eclipse.mylyn"],
    "RAP": ["org.eclipse.rap"],
    "PTP": ["ptp"],
    "SCOUT": ["scout.rt"],
    "WEBTOOLS": ["webtools.javaee"],
    "WINDOWBUILDER": ["windowbuilder"]
}

target_features = list(repo_map.keys())

def run_git(cmd, cwd):
    try:
        result = subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True, check=True, timeout=30)
        return result.stdout.strip().split('\n')
    except subprocess.TimeoutExpired:
        print(f"    -> Timeout no Git ({cmd})", flush=True)
        return []
    except Exception as e:
        return []

def get_commit(tag, cwd):
    res = run_git(["rev-list", "-n", "1", tag], cwd)
    return res[0] if res else None

def heuristic_0_timestamp(version, repo_dir):
    """
    Time-Travel Heuristic (The Silver Bullet for Eclipse builds)
    Extracts YYYYMMDDHHMM from version (e.g. 12.4.0.202603041756)
    and asks git for the latest commit before that exact second.
    """
    match = re.search(r'\.(\d{12})$', version)
    if match:
        ts = match.group(1)
        # Format: YYYYMMDDHHMM to YYYY-MM-DD HH:MM:00
        dt_str = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:00"
        
        # Look for the last commit on any branch up to that date
        res = run_git(["log", f"--until={dt_str}", "--format=%H", "-1", "--all"], cwd=repo_dir)
        if res and res[0]:
            return dt_str, res[0]
            
    return None

def heuristic_1_tags(version, repo_dir):
    tags = run_git(["tag"], cwd=repo_dir)
    if not tags or tags == ['']: return None
    
    clean_v = re.sub(r'\.\d{12}$', '', version)
    parts = clean_v.split('.')
    if len(parts) >= 2:
        major, minor = parts[0], parts[1]
        patch = parts[2] if len(parts) > 2 else "0"
        
        candidates = [
            f"v{major}.{minor}.{patch}", f"v{major}.{minor}",
            f"R{major}_{minor}_{patch}", f"R{major}_{minor}",
            f"{major}.{minor}.{patch}",
            f"CDT_{major}_{minor}_{patch}", f"CDT_{major}_{minor}",
            f"R_{major}_{minor}_{patch}", f"R_{major}_{minor}",
            clean_v, version
        ]
        
        candidates_lower = [c.lower() for c in candidates]
        
        for t in tags:
            tl = t.lower()
            if tl in candidates_lower or tl == clean_v.lower() or tl == f"v{clean_v.lower()}" or tl.endswith(f"-{clean_v.lower()}"):
                return t, get_commit(t, repo_dir)
                
    return None

def heuristic_2_pickaxe(version, repo_dir):
    clean_v = re.sub(r'\.\d{12}$', '', version)
    search_str = f"Bundle-Version: {clean_v}"
    
    res = run_git(["log", "-S", search_str, "--format=%H", "-1", "--all"], cwd=repo_dir)
    if res and res[0]:
        return res[0]
        
    search_str2 = f"<version>{clean_v}</version>"
    res2 = run_git(["log", "-S", search_str2, "--format=%H", "-1", "--all"], cwd=repo_dir)
    if res2 and res2[0]:
        return res2[0]
        
    return None

def heuristic_3_train_tags(release_name, repo_dir):
    tags = run_git(["tag"], cwd=repo_dir)
    if not tags or tags == ['']: return None
    
    train_aliases = [release_name]
    rl = release_name.lower()
    if rl == "neon": train_aliases += ["Neon", "neon_R", "R4_6"]
    elif rl == "oxygen": train_aliases += ["Oxygen", "oxygen_R", "R4_7"]
    elif release_name == "2018-09": train_aliases += ["simrel-2018-09", "2018-09", "R4_9"]
    elif release_name == "2026-03": train_aliases += ["simrel-2026-03", "2026-03", "R4_39"]
    
    for alias in train_aliases:
        for t in tags:
            if t.lower() == alias.lower() or t.lower() == f"v{alias.lower()}":
                return t, get_commit(t, repo_dir)
                
    return None

# Process all .json files in the directory
target_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]

print(f"Encontrados {len(target_files)} arquivos de release para mapear.")

for file in target_files:
    filepath = os.path.join(json_dir, file)
    print(f"Processando {file}...")
    
    mapping_data = {
        "release": "",
        "mappings": {}
    }
    out_filepath = os.path.join(out_dir, file)
    if os.path.exists(out_filepath):
        print(f"Skipping {file}, já processado.", flush=True)
        continue
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        release = data.get("release", file.replace(".json", ""))
        mapping_data["release"] = release
        
        for feat in target_features:
            feature_data = data.get("features", {}).get(feat)
            if not feature_data: 
                continue
            
            version = feature_data.get("version")
            if not version or version == "N/A": 
                mapping_data["mappings"][feat] = {
                    "version": version, "status": "SKIPPED", "commit": None, 
                    "heuristic_id": None, "heuristic_description": None, "matched_value": None, "repository": None
                }
                continue
                
            found = False
            for repo_name in repo_map[feat]:
                repo_dir = os.path.join(base_dir, repo_name)
                if not os.path.exists(repo_dir): continue
                
                print(f"  Buscando {feat} ({version}) no repositório {repo_name}...", flush=True)
                
                h0 = heuristic_0_timestamp(version, repo_dir)
                if h0 and h0[1]:
                    mapping_data["mappings"][feat] = {
                        "version": version, "status": "SUCCESS", "commit": h0[1], 
                        "heuristic_id": "H0", "heuristic_description": "Timestamp Time-Travel", "matched_value": h0[0], "repository": repo_name
                    }
                    found = True; break
                
                h1 = heuristic_1_tags(version, repo_dir)
                if h1 and h1[1]:
                    mapping_data["mappings"][feat] = {
                        "version": version, "status": "SUCCESS", "commit": h1[1], 
                        "heuristic_id": "H1", "heuristic_description": "Fuzzy Tag Matching", "matched_value": h1[0], "repository": repo_name
                    }
                    found = True; break
                    
                h3 = heuristic_3_train_tags(release, repo_dir)
                if h3 and h3[1]:
                    mapping_data["mappings"][feat] = {
                        "version": version, "status": "SUCCESS", "commit": h3[1], 
                        "heuristic_id": "H3", "heuristic_description": "Release Train Tagging", "matched_value": h3[0], "repository": repo_name
                    }
                    found = True; break
                    
                print(f"    -> Fallback para Pickaxe (lento)...", flush=True)
                h2 = heuristic_2_pickaxe(version, repo_dir)
                if h2:
                    mapping_data["mappings"][feat] = {
                        "version": version, "status": "SUCCESS", "commit": h2, 
                        "heuristic_id": "H2", "heuristic_description": "Git Log Pickaxe (MANIFEST.MF)", "matched_value": version, "repository": repo_name
                    }
                    found = True; break
                    
            if not found:
                print(f"    -> NOT FOUND", flush=True)
                mapping_data["mappings"][feat] = {
                    "version": version, "status": "NOT FOUND", "commit": None, 
                    "heuristic_id": None, "heuristic_description": None, "matched_value": None, "repository": None
                }

    out_filepath = os.path.join(out_dir, file)
    with open(out_filepath, "w", encoding="utf-8") as out_f:
        json.dump(mapping_data, out_f, indent=4, ensure_ascii=False)

print(f"Mapeamento concluído em {len(target_files)} releases. Resultados salvos em {out_dir}")
