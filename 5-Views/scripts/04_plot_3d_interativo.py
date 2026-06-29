import pandas as pd
import os

try:
    import plotly.express as px
except ImportError:
    import subprocess
    import sys
    print("Plotly não encontrado. Instalando temporariamente...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.express as px

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
csv_path = os.path.join(base_dir, r"5-Views\resultados\02_clusterizacao\clusterizacao_resultados.csv")
out_dir = os.path.join(base_dir, r"5-Views\resultados\02_clusterizacao")

df = pd.read_csv(csv_path)

color_discrete_map = {
    'C1: Enxutas e Estáveis': '#2ca02c', 
    'C2: Médias': '#ff7f0e', 
    'C3: Gigantes Voláteis': '#d62728'
}

fig = px.scatter_3d(
    df, 
    x='Tamanho_Norm', 
    y='Complexidade_Norm', 
    z='Mudanca_Norm',
    color='Perfil_Cluster',
    text='feature',
    color_discrete_map=color_discrete_map,
    title="Projeção 3D Interativa dos Clusters Evolutivos (Espaço do K-Means)",
    labels={
        'Tamanho_Norm': 'Tamanho (Norm)',
        'Complexidade_Norm': 'Complexidade (Norm)',
        'Mudanca_Norm': 'Mudanças Acumuladas (Norm)',
        'Perfil_Cluster': 'Cluster'
    }
)

# Ajustar tamanho das bolhas e fonte para ficar bem visível
fig.update_traces(marker=dict(size=8, line=dict(width=1, color='DarkSlateGrey')),
                  textfont_size=16)

fig.update_layout(
    scene=dict(
        xaxis=dict(backgroundcolor="white", gridcolor="lightgrey", showbackground=True, zerolinecolor="white"),
        yaxis=dict(backgroundcolor="white", gridcolor="lightgrey", showbackground=True, zerolinecolor="white"),
        zaxis=dict(backgroundcolor="white", gridcolor="lightgrey", showbackground=True, zerolinecolor="white"),
    ),
    margin=dict(l=0, r=0, b=0, t=40),
    font=dict(size=14)
)

save_path = os.path.join(out_dir, "scatter_3d_clusters_interativo.html")
fig.write_html(save_path)
print(f"Salvo: {save_path}")
