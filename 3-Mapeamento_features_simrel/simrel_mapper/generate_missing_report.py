import json
import os
from pathlib import Path

def main():
    output_dir = Path(r"c:\Users\Kevin Strey\Desktop\Feature-models\3-Mapeamento_features_simrel\simrel_mapper\output")
    
    EXPECTED_FEATURES = {
        "JDT": ["JDT"],
        "PDE": ["PDE"],
        "Scout": ["Scout"],
        "Maven": ["m2e", "m2e-core"],
        "EMF": ["EMF (Core)", "org.eclipse.emf"],
        "GMF": ["GMF Runtime", "gmf-runtime"],
        "Datatools": ["DataTools", "datatools"],
        "BIRT": ["BIRT", "birt"],
        "GEF": ["GEF", "gef-classic"],
        "CDT": ["CDT", "cdt"],
        "CVS": ["CVS"],
        "WebTools": ["WebTools", "webtools", "webtools.javaee", "web tools", "web tools platform"],
        "SVN": ["Subversive", "SVN"],
        "Mylyn": ["Mylyn", "org.eclipse.mylyn"],
        "PTP": ["PTP", "ptp"],
        "Jubula": ["Jubula"],
        "RAP": ["RAP Tools", "RAP Runtime", "RAP"],
        "EGit": ["EGit", "egit"],
        "EclipseLink": ["EclipseLink", "eclipselink"],
        "WindowBuilder": ["Window Builder", "WindowBuilder", "windowbuilder"]
    }
    
    def is_retired(feature: str, release_name: str) -> bool:
        if feature == "Jubula": return True
        if not release_name.startswith("20"):
            if feature == "CVS" and "Neon" in release_name: return True
            return False
            
        try:
            year = int(release_name[:4])
            month = int(release_name[5:7]) if len(release_name) >= 7 and release_name[5:7].isdigit() else 0
        except:
            return False
            
        if feature == "CVS": return True
        if feature == "EclipseLink" and (year > 2018 or (year == 2018 and month >= 9)): return True
        if feature == "Datatools" and (year > 2018 or (year == 2018 and month >= 12)): return True
        if feature == "SVN" and (year > 2018 or (year == 2018 and month >= 12)): return True
        if feature == "BIRT" and (year > 2020 or (year == 2020 and month >= 12)): return True
        if feature == "PTP" and (year >= 2026): return True
        
        return False
    
    # Dicionário para armazenar o resumo
    not_found_summary = {}

    print(f"Lendo arquivos de: {output_dir}")
    
    # Varre todos os arquivos .json gerados pelas análises
    for file_path in output_dir.glob("*.json"):
        if not file_path.is_file():
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Erro ao ler {file_path.name}: {e}")
            continue
            
        release_name = data.get("release", file_path.stem)
        mappings = data.get("mappings", {})
        # Filtra as features baseadas no gabarito
        missing_features = {}
        for feature_name, possible_keys in EXPECTED_FEATURES.items():
            
            found = False
            for alias in possible_keys:
                if alias in mappings:
                    info = mappings[alias]
                    if info.get('status') in ['SUCCESS', 'NEEDS REVIEW'] and info.get('commit'):
                        found = True
                        break
                    else:
                        missing_features[feature_name] = {'status': 'NOT FOUND', 'details': info}
                        found = True
                        break
            
            if not found:
                for alias in possible_keys:
                    alias_lower = alias.lower()
                    for json_key in mappings.keys():
                        if json_key.lower().startswith(alias_lower):
                            info = mappings[json_key]
                            if info.get('status') in ['SUCCESS', 'NEEDS REVIEW'] and info.get('commit'):
                                found = True
                                break
                            else:
                                missing_features[feature_name] = {'status': 'NOT FOUND', 'details': info}
                                found = True
                                break
                    if found:
                        break
            if not found:
                for alias in possible_keys:
                    # Match de prefixo
                    alias_lower = alias.lower()
                    for json_key in mappings.keys():
                        if json_key.lower().startswith(alias_lower):
                            info = mappings[json_key]
                            if info.get("status") in ["SUCCESS", "NEEDS REVIEW"] and info.get("commit"):
                                found = True
                                break
                    if found:
                        break
            
            if not found:
                if not is_retired(feature_name, release_name):
                    missing_features[feature_name] = {"status": "MISSING_IN_JSON", "details": "Nenhum dos aliases foi achado na extração"}
            
            if feature_name in missing_features and is_retired(feature_name, release_name):
                del missing_features[feature_name]
                
        if missing_features:
            not_found_summary[release_name] = missing_features
            
    # Salva o resultado final em um único arquivo de resumo
    summary_path = output_dir / "summary_not_found.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(not_found_summary, f, indent=2, ensure_ascii=False)
        
    print(f"Sucesso! Resumo unificado gerado em: {summary_path}")
    print(f"Total de releases que ainda possuem itens 'NOT FOUND': {len(not_found_summary)}")

if __name__ == "__main__":
    main()
