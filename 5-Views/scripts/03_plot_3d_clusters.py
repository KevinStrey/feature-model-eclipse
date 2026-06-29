import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib

# Configurar matplotlib para não usar interface gráfica e usar fontes acadêmicas
matplotlib.use('Agg')
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 15,
    'figure.dpi': 300,
    'savefig.dpi': 300
})

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
csv_path = os.path.join(base_dir, r"5-Views\resultados\02_clusterizacao\clusterizacao_resultados.csv")
out_dir = os.path.join(base_dir, r"5-Views\resultados\02_clusterizacao")

df = pd.read_csv(csv_path)

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Vamos usar as métricas normalizadas para mostrar exatamente o espaço tridimensional que o K-Means "enxergou"
x_col = 'Tamanho_Norm'
y_col = 'Complexidade_Norm'
z_col = 'Mudanca_Norm'

colors = {'C1: Enxutas e Estáveis': '#2ca02c', 'C2: Médias': '#ff7f0e', 'C3: Gigantes Voláteis': '#d62728'}

for cluster_name, color in colors.items():
    subset = df[df['Perfil_Cluster'] == cluster_name]
    ax.scatter(subset[x_col], 
               subset[y_col], 
               subset[z_col], 
               c=color, label=cluster_name, s=100, edgecolors='k', alpha=0.8)

    # Anotar os nomes das features para visualização
    for i, row in subset.iterrows():
        ax.text(row[x_col], row[y_col], row[z_col], f" {row['feature']}", size=16, zorder=1, color='k')

ax.set_xlabel('Tamanho (Normalizado)')
ax.set_ylabel('Complexidade (Normalizada)')
ax.set_zlabel('Mudanças Acumuladas (Normalizado)')
ax.set_title('Projeção 3D dos Clusters Evolutivos (Espaço Euclidiano do K-Means)')

ax.legend()

# Ajustar o ângulo de visualização para favorecer a separação visual da Complexidade (eixo Y)
ax.view_init(elev=15., azim=190)

plt.tight_layout()
save_path = os.path.join(out_dir, "scatter_3d_clusters.pdf")
plt.savefig(save_path, bbox_inches='tight')
print(f"Salvo: {save_path}")
