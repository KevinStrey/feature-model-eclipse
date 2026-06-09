import json
import os
import subprocess
import re

dados_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models\releases\dados-features"
mappings_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models\releases\mappings"
m2e_repo = r"c:\Users\Kevin Strey\Desktop\Feature-models\m2e-core"

def run_git(cmd, cwd):
    try:
        result = subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True, check=True, timeout=30)
        return result.stdout.strip().split('\n')
    except subprocess.TimeoutExpired:
        return []
    except Exception as e:
        return []

def get_git_tags(cwd):
    return run_git(["tag"], cwd)

def heuristic_0_timestamp(version_str, cwd):
    match = re.search(r'\d{8}\d{4}', version_str)
    if not match:
        return None
    timestamp_str = match.group(0)
    year, month, day, hour, minute = timestamp_str[:4], timestamp_str[4:6], timestamp_str[6:8], timestamp_str[8:10], timestamp_str[10:12]
    git_date = f"{year}-{month}-{day} {hour}:{minute}:00"
    res = run_git(["log", f"--until={git_date}", "-1", "--format=%H"], cwd)
    if res and res[0]:
        return {"commit": res[0], "matched_value": git_date, "h_id": "H0", "h_desc": "Timestamp Time-Travel"}
    return None

def heuristic_1_tags(version_str, cwd, tags):
    base_version = re.sub(r'\.v\d{8}.*$', '', version_str)
    base_version = re.sub(r'v\d{8}.*$', '', base_version)
    base_version = re.sub(r'\.\d{8}.*$', '', base_version)
    parts = base_version.split('.')
    while len(parts) < 3:
        parts.append('0')
    major, minor, patch = parts[0], parts[1], parts[2]

    candidates = [
        f"releases/{major}.{minor}.{patch}",
        f"releases/{major}.{minor}.{patch}.Final",
        f"releases/{major}.{minor}/{major}.{minor}.{patch}",
        f"v{major}.{minor}.{patch}",
        f"{major}.{minor}.{patch}",
        f"R{major}_{minor}_{patch}",
        f"R{major}_{minor}",
        f"{major}.{minor}"
    ]
    
    for cand in candidates:
        if cand in tags:
            res = run_git(["rev-list", "-n", "1", cand], cwd)
            if res and res[0]:
                return {"commit": res[0], "matched_value": cand, "h_id": "H1", "h_desc": "Fuzzy Tag Matching"}
    return None

def heuristic_2_pickaxe(version_str, cwd):
    base_version = re.sub(r'\.v\d{8}.*$', '', version_str)
    base_version = re.sub(r'\.\d{8}.*$', '', base_version)
    search_str = f"Bundle-Version: {base_version}"
    res = run_git(["log", "-S", search_str, "--format=%H", "-1"], cwd)
    if res and res[0]:
        return {"commit": res[0], "matched_value": base_version, "h_id": "H2", "h_desc": "Git Log Pickaxe (MANIFEST.MF)"}
    return None

def heuristic_manual_fallback(mappings, cwd):
    # Encontrar timestamp do H0 em outras features
    ref_time = None
    for feat, info in mappings.items():
        if info.get("status") == "SUCCESS" and info.get("heuristic_id") == "H0":
            ref_time = info.get("matched_value")
            break
    if not ref_time:
        for feat, info in mappings.items():
            if info.get("status") == "SUCCESS" and "20" in str(info.get("matched_value")):
                val = str(info.get("matched_value"))
                if len(val) >= 10 and "-" in val:
                    ref_time = val
                    break
    
    if ref_time:
        res = run_git(["log", f"--until={ref_time}", "-1", "--format=%H"], cwd)
        if res and res[0]:
            return {"commit": res[0], "matched_value": ref_time, "h_id": "H_MANUAL", "h_desc": f"Inferred via related Timestamp ({ref_time})"}
    return None

print("Atualizando MAVEN em todos os mapeamentos...")
tags = get_git_tags(m2e_repo)
count_success = 0
count_total = 0

for file in sorted(os.listdir(dados_dir)):
    if not file.endswith(".json"): continue
    count_total += 1
    
    dados_path = os.path.join(dados_dir, file)
    with open(dados_path, 'r', encoding='utf-8') as f:
        dados = json.load(f)
        
    maven_data = dados.get("features", {}).get("MAVEN")
    if not maven_data or maven_data.get("version") == "N/A":
        # Sem maven nesta release
        continue
        
    version = maven_data["version"]
    
    mapping_path = os.path.join(mappings_dir, file)
    if not os.path.exists(mapping_path):
        continue
        
    with open(mapping_path, 'r', encoding='utf-8') as f:
        map_data = json.load(f)
        
    mappings = map_data.setdefault("mappings", {})
    
    # Executar Heurísticas
    result = heuristic_0_timestamp(version, m2e_repo)
    if not result:
        result = heuristic_1_tags(version, m2e_repo, tags)
    if not result:
        result = heuristic_2_pickaxe(version, m2e_repo)
    if not result:
        result = heuristic_manual_fallback(mappings, m2e_repo)
        
    if result:
        mappings["MAVEN"] = {
            "version": version,
            "status": "SUCCESS",
            "commit": result["commit"],
            "heuristic_id": result["h_id"],
            "heuristic_description": result["h_desc"],
            "matched_value": result["matched_value"],
            "repository": "m2e-core"
        }
        count_success += 1
    else:
        mappings["MAVEN"] = {
            "version": version,
            "status": "NOT FOUND",
            "commit": None,
            "heuristic_id": None,
            "heuristic_description": None,
            "matched_value": None,
            "repository": "m2e-core"
        }
        print(f"[{file}] MAVEN {version} -> NOT FOUND")
        
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(map_data, f, indent=4)

print(f"Concluído! MAVEN mapeado com sucesso em {count_success} de {count_total} releases.")
