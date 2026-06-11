import json
import os
from pathlib import Path

# Mapeia qual Node no diagrama procura por quais chaves possíveis no JSON
NODE_JSON_KEYS = {
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
    "WebTools": ["WebTools", "webtools.javaee", "webtools", "web tools", "web tools platform"],
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
    """Verifica se a feature já estava descontinuada na release atual."""
    if feature == "Jubula": return True
    if not release_name.startswith("20"):
        # Releases velhas (Juno, Kepler, etc)
        if feature == "CVS" and "Neon" in release_name: return True # Aproximado
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

DOT_TEMPLATE = """digraph G {
    rankdir=TB;
    splines=false;
    nodesep=0.15;
    ranksep=0.4;
    
    node [
        shape=box,
        style="filled,rounded",
        fontname="Arial",
        fontsize=10,
        color="#707070",
        fillcolor="#FFFFFF",
        height=0.3,
        width=1.0
    ];
    
    edge [
        fontname="Arial",
        fontsize=8,
        arrowsize=0.8,
        color="#707070"
    ];
    
    // Core structure nodes
    EclipseIDE [label="EclipseIDE", fillcolor="#E3F2FD", fontname="Arial bold", fontsize=11];
    RCP_Platform [label="RCP_Platform", fillcolor="#FFF9C4", fontname="Arial bold", fontsize=11];
    
    // Feature nodes
{feature_nodes}
    
    // Edges (Feature model constraints)
    EclipseIDE -> RCP_Platform [arrowhead=dot];
    
    RCP_Platform -> JDT [arrowhead=odot];
    RCP_Platform -> EMF [arrowhead=odot];
    RCP_Platform -> GEF [arrowhead=odot];
    RCP_Platform -> CDT [arrowhead=odot];
    RCP_Platform -> CVS [arrowhead=odot];
    RCP_Platform -> WebTools [arrowhead=odot];
    RCP_Platform -> SVN [arrowhead=odot];
    RCP_Platform -> Mylyn [arrowhead=odot];
    RCP_Platform -> PTP [arrowhead=odot];
    RCP_Platform -> Jubula [arrowhead=odot];
    RCP_Platform -> RAP [arrowhead=odot];
    RCP_Platform -> EGit [arrowhead=odot];
    RCP_Platform -> EclipseLink [arrowhead=odot];
    RCP_Platform -> WindowBuilder [arrowhead=odot];
    
    JDT -> PDE [arrowhead=odot];
    JDT -> Maven [arrowhead=odot];
    
    PDE -> Scout [arrowhead=odot];
    
    EMF -> GMF [arrowhead=odot];
    EMF -> Datatools [arrowhead=odot];
    
    Datatools -> BIRT [arrowhead=odot];
    
    // Laying out elements to align horizontally
    { rank=same; JDT; EMF; GEF; CDT; CVS; WebTools; SVN; Mylyn; PTP; Jubula; RAP; EGit; EclipseLink; WindowBuilder; }
    { rank=same; PDE; Maven; GMF; Datatools; }
    { rank=same; Scout; BIRT; }
}
"""

def extract_version_from_json(mappings: dict, possible_keys: list) -> str:
    """Busca a versão no JSON mapeado, testando as chaves exatas e também por prefixo."""
    for key in possible_keys:
        # Match exato
        if key in mappings:
            info = mappings[key]
            version = info.get("version")
            if version is None:
                version = "UNKNOWN"
            timestamp = info.get("timestamp")
            if timestamp and timestamp not in version:
                return f"v{version}.{timestamp}"
            elif version:
                return f"v{version}"
                
        # Match por prefixo (ex: "WebTools 3.12 for Simrel 2018-12" -> "WebTools")
        key_lower = key.lower()
        for json_key, info in mappings.items():
            if json_key.lower().startswith(key_lower):
                version = info.get("version")
                if version is None:
                    version = "UNKNOWN"
                timestamp = info.get("timestamp")
                if timestamp and timestamp not in version:
                    return f"v{version}.{timestamp}"
                elif version:
                    return f"v{version}"
    return "NOT FOUND"

def main():
    base_path = Path(r"c:\Users\Kevin Strey\Desktop\Feature-models\3-Mapeamento_features_simrel\simrel_mapper")
    output_dir = base_path / "output"
    diagrams_dir = Path(r"c:\Users\Kevin Strey\Desktop\Feature-models\releases\diagramas")
    
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    
    for json_file in output_dir.glob("*.json"):
        if not json_file.is_file():
            continue
            
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
            
        release = data.get("release", json_file.stem)
        mappings = data.get("mappings", {})
        
        feature_nodes_str = ""
        node_lines = []
        for node_name, keys in NODE_JSON_KEYS.items():
            version_str = extract_version_from_json(mappings, keys)
            
            if version_str != "NOT FOUND":
                label = f"{node_name}\\n({version_str})"
                fillcolor = "#C8E6C9"
                node_lines.append(f'    {node_name} [label="{label}", fillcolor="{fillcolor}"];')
            else:
                # Pinta de vermelho e muda a label se for erro, ou cinza tracejado se aposentado
                if is_retired(node_name, release):
                    node_label = f'{node_name}\\n(RETIRED)'
                    color = '"#E0E0E0"'  # Cinza claro
                    fontcolor = '"#888888"'
                    style = '"filled,rounded,dashed"'
                    node_lines.append(f'    {node_name} [label="{node_label}", fillcolor={color}, fontcolor={fontcolor}, style={style}];')
                else:
                    node_label = f'{node_name}\\n(NOT FOUND)'
                    color = '"#FFCDD2"'  # Vermelho claro
                    node_lines.append(f'    {node_name} [label="{node_label}", fillcolor={color}];')
            
        final_dot = DOT_TEMPLATE.replace("{feature_nodes}", "\n".join(node_lines))
        
        dot_file = diagrams_dir / f"{release}.dot"
        with open(dot_file, "w", encoding="utf-8") as f:
            f.write(final_dot)
            
    print(f"Diagramas .dot gerados com sucesso na pasta: {diagrams_dir}")

if __name__ == "__main__":
    main()
