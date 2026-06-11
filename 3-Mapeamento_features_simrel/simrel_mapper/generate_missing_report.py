import json
import os
from pathlib import Path

def main():
    output_dir = Path(r"c:\Users\Kevin Strey\Desktop\Feature-models\3-Mapeamento_features_simrel\simrel_mapper\output")
    
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
        
        # Filtra apenas as features que não foram encontradas
        missing_features = {}
        for feature, info in mappings.items():
            if info.get("status") == "NOT FOUND" or not info.get("commit"):
                missing_features[feature] = info
                
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
