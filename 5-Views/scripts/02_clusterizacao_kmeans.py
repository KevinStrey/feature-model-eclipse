import pandas as pd
import numpy as np
import os
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
from math import pi
import warnings

warnings.filterwarnings('ignore')
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['savefig.dpi'] = 300

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
csv_path = os.path.join(base_dir, r"5-Views\resultados\01_extracao_base\classificacao_features.csv")
out_dir = os.path.join(base_dir, r"5-Views\resultados\02_clusterizacao")

# Criar pastas
os.makedirs(out_dir, exist_ok=True)
os.makedirs(os.path.join(out_dir, "features"), exist_ok=True)

print("Carregando base de dados para clusterização...")
df = pd.read_csv(csv_path, encoding='latin1', sep=';')

# Selecionar as 3 métricas principais que representam nossos eixos
# 1. Tamanho: Initial_LOC
# 2. Complexidade: Initial_Complexity (Recalculado para evitar corrupção de floats)
# 3. Mudança: CSB (Changes Since Birth - Commits acumulados)

# Recalcular a complexidade ignorando o valor corrompido do CSV
df['Initial_Complexity'] = df['Initial_LOC'] / df['Initial_Methods']
# Preencher possíveis NaNs caso Initial_Methods seja 0
df['Initial_Complexity'] = df['Initial_Complexity'].fillna(0.0)

metrics = ['Initial_LOC', 'Initial_Complexity', 'CSB']
X = df[metrics].values

# 1. Normalização Min-Max (0 a 1)
X_min = X.min(axis=0)
X_max = X.max(axis=0)
X_norm = (X - X_min) / (X_max - X_min)

# Salvar valores normalizados no dataframe
df['Tamanho_Norm'] = X_norm[:, 0]
df['Complexidade_Norm'] = X_norm[:, 1]
df['Mudanca_Norm'] = X_norm[:, 2]

# 2. K-Means Clustering (NumPy puro)
def k_means(data, k=3, max_iters=100, seed=42):
    np.random.seed(seed)
    # Escolher k centróides aleatoriamente
    initial_indices = np.random.choice(data.shape[0], k, replace=False)
    centroids = data[initial_indices]
    
    for _ in range(max_iters):
        # Distância Euclidiana de todos os pontos para todos os centróides
        distances = np.linalg.norm(data[:, np.newaxis] - centroids, axis=2)
        labels = np.argmin(distances, axis=1)
        
        new_centroids = np.array([
            data[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
            for i in range(k)
        ])
        
        if np.allclose(centroids, new_centroids):
            break
        centroids = new_centroids
        
    return labels, centroids

print("Treinando K-Means (K=3)...")
labels, centroids = k_means(X_norm, k=3)

# Identificar qual cluster é qual baseado nos centróides
# O cluster com maior média de Tamanho+Mudança geralmente é o de "Grandes", etc.
# Para evitar nomes genéricos, vamos manter Cluster 0, 1 e 2, mas dar um apelido.
cluster_scores = centroids.sum(axis=1)
order = np.argsort(cluster_scores) # do menor impacto para o maior
nomes = {}
nomes[order[0]] = "C1: Enxutas e Estáveis"
nomes[order[1]] = "C2: Médias"
nomes[order[2]] = "C3: Gigantes Voláteis"

df['Cluster_ID'] = labels
df['Perfil_Cluster'] = df['Cluster_ID'].map(nomes)

# Salvar CSV com os resultados
df.to_csv(os.path.join(out_dir, "clusterizacao_resultados.csv"), index=False)

print("Gerando gráficos globais...")

# --- GRÁFICOS GLOBAIS ---
# A) Pie Chart (Distribuição)
plt.figure(figsize=(8, 8))
cluster_counts = df['Perfil_Cluster'].value_counts()
plt.pie(cluster_counts, labels=cluster_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("Set2"))
plt.title("Distribuição do Ecossistema em Perfis de Evolução")
plt.savefig(os.path.join(out_dir, "piechart_clusters.pdf"), bbox_inches='tight')
plt.close()

# B) Bar Chart de Perfil do Cluster
cluster_means = df.groupby('Perfil_Cluster')[['Tamanho_Norm', 'Complexidade_Norm', 'Mudanca_Norm']].mean().reset_index()
# Derreter (melt) para facilitar o seaborn barplot
melted_means = pd.melt(cluster_means, id_vars='Perfil_Cluster', var_name='Métrica', value_name='Score Médio (0 a 1)')
plt.figure(figsize=(10, 6))
sns.barplot(data=melted_means, x='Perfil_Cluster', y='Score Médio (0 a 1)', hue='Métrica', palette="mako")
plt.title("O que define cada Perfil? (Score Médio por Cluster)")
plt.savefig(os.path.join(out_dir, "barchart_perfil_clusters.pdf"), bbox_inches='tight')
plt.close()

# C) Scatter 2D (Tamanho vs Mudança) Colorido por Cluster
plt.figure(figsize=(10, 8))
sns.scatterplot(data=df, x='Initial_LOC', y='CSB', hue='Perfil_Cluster', palette="Set2", s=150, alpha=0.8)
for i, txt in enumerate(df['feature']):
    plt.annotate(txt, (df['Initial_LOC'].iloc[i], df['CSB'].iloc[i]), fontsize=8, alpha=0.7)
plt.title("Fronteira dos Clusters: Tamanho vs Mudança de Código")
plt.xlabel("Tamanho Inicial (LOC)")
plt.ylabel("Mudança (Commits Desde Nascimento - CSB)")
plt.savefig(os.path.join(out_dir, "scatter_simples_tamanho_vs_mudanca.pdf"), bbox_inches='tight')
plt.close()

print("Gerando gráficos de Radar individuais por Feature...")

# --- GRÁFICOS DE RADAR INDIVIDUAIS ---
# Função para plotar radar
def make_radar_chart(feature_name, sizes, title, save_path):
    # sizes é uma lista: [tamanho, complexidade, mudanca]
    categories = ['Tamanho\n(LOC)', 'Complexidade\n(LOC/Método)', 'Mudança\n(CSB)']
    N = len(categories)
    
    # Calcular os ângulos
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    values = sizes.tolist()
    values += values[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    
    # Desenhar grid e labels
    plt.xticks(angles[:-1], categories, color='grey', size=12)
    ax.set_rlabel_position(0)
    plt.yticks([0.25, 0.5, 0.75, 1.0], ["25%", "50%", "75%", "100%"], color="grey", size=8)
    plt.ylim(0, 1.1)
    
    # Plotar os dados
    ax.plot(angles, values, linewidth=2, linestyle='solid', color='darkblue')
    ax.fill(angles, values, 'b', alpha=0.25)
    
    plt.title(title, size=16, color='black', y=1.1)
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()

for i, row in df.iterrows():
    feat_name = row['feature']
    perfil = row['Perfil_Cluster']
    # Scores de 0 a 1
    scores = row[['Tamanho_Norm', 'Complexidade_Norm', 'Mudanca_Norm']].values
    
    title = f"{feat_name}\nPerfil: {perfil}"
    save_path = os.path.join(out_dir, "features", f"{feat_name}.pdf")
    
    make_radar_chart(feat_name, scores, title, save_path)

print(f"Processo concluído com sucesso! Verifique a pasta {out_dir}")
