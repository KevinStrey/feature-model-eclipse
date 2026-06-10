import json
import os
import subprocess

mappings_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models\releases\mappings"
repo_map = {
    "SCOUT": r"c:\Users\Kevin Strey\Desktop\Feature-models\scout.rt",
    "DATATOOLS": r"c:\Users\Kevin Strey\Desktop\Feature-models\datatools",
    "WEBTOOLS": r"c:\Users\Kevin Strey\Desktop\Feature-models\webtools.javaee",
    "MYLYN": r"c:\Users\Kevin Strey\Desktop\Feature-models\org.eclipse.mylyn",
    "WINDOWBUILDER": r"c:\Users\Kevin Strey\Desktop\Feature-models\windowbuilder"
}

def run_git_until(timestamp, repo_dir):
    try:
        # Pega a data YYYY-MM-DD HH:MM:SS
        cmd = ["git", "log", f"--until={timestamp}", "-1", "--format=%H"]
        result = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, check=True)
        commit = result.stdout.strip()
        return commit if commit else None
    except Exception as e:
        return None

fixed_log = []

for file in sorted(os.listdir(mappings_dir)):
    if not file.endswith(".json"):
        continue
        
    filepath = os.path.join(mappings_dir, file)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    mappings = data.get("mappings", {})
    
    # Encontrar um timestamp de referência no arquivo (idealmente de JDT, PDE ou CDT)
    reference_timestamp = None
    for feat, info in mappings.items():
        if info.get("status") == "SUCCESS" and info.get("heuristic_id") == "H0":
            reference_timestamp = info.get("matched_value")
            break
            
    if not reference_timestamp:
        # Fallback para qualquer outro timestamp se JDT/CDT não for H0 (raro)
        for feat, info in mappings.items():
            if info.get("status") == "SUCCESS" and "20" in str(info.get("matched_value")):
                # Checa se parece um timestamp
                val = str(info.get("matched_value"))
                if len(val) >= 10 and "-" in val:
                    reference_timestamp = val
                    break

    needs_save = False
    
    # Primeiro resolvemos tudo exceto ECLIPSELINK (porque ele precisa do WEBTOOLS pronto)
    for feat in list(mappings.keys()):
        if feat == "ECLIPSELINK":
            continue
            
        info = mappings[feat]
        if info.get("status") == "NOT FOUND":
            if feat in repo_map and reference_timestamp:
                repo_dir = repo_map[feat]
                commit = run_git_until(reference_timestamp, repo_dir)
                if commit:
                    info["status"] = "SUCCESS"
                    info["commit"] = commit
                    info["heuristic_id"] = "H_MANUAL"
                    info["heuristic_description"] = f"Inferred via related Timestamp ({reference_timestamp})"
                    info["matched_value"] = reference_timestamp
                    needs_save = True
                    fixed_log.append(f"{file} | {feat} | {info['version']} | {commit} (via Time-Travel)")

    # Agora resolvemos ECLIPSELINK copiando do WEBTOOLS
    if "ECLIPSELINK" in mappings and mappings["ECLIPSELINK"].get("status") == "NOT FOUND":
        wtp_info = mappings.get("WEBTOOLS")
        if wtp_info and wtp_info.get("status") == "SUCCESS":
            info = mappings["ECLIPSELINK"]
            info["status"] = "SUCCESS"
            info["commit"] = wtp_info["commit"]
            info["heuristic_id"] = "H_MANUAL"
            info["heuristic_description"] = "Copied from WEBTOOLS"
            info["matched_value"] = wtp_info["version"]
            needs_save = True
            fixed_log.append(f"{file} | ECLIPSELINK | {info['version']} | {wtp_info['commit']} (Copied from WTP)")
            
    if needs_save:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

# Gerar relatório
report_path = r"C:\Users\Kevin Strey\.gemini\antigravity-ide\brain\1991ee3f-ecac-4d4d-862f-6f7bf0cbe251\fixed_mappings_report.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("# Relatório de Correções de Mapeamento (Fallback Manual)\n\n")
    f.write("| Arquivo | Feature | Versão | Correção / Commit |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    for log in fixed_log:
        f.write(f"| {log.split(' | ')[0]} | {log.split(' | ')[1]} | {log.split(' | ')[2]} | `{log.split(' | ')[3]}` |\n")

print(f"Foram corrigidas {len(fixed_log)} features.")
