import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
csv_path = os.path.join(base_dir, r"5-Views\resultados\01_extracao_base\classificacao_features.csv")
out_dir = os.path.join(base_dir, r"5-Views\resultados\02_clusterizacao")

# Criar pastas
os.makedirs(out_dir, exist_ok=True)

df = pd.read_csv(csv_path, encoding='latin1', sep=';')

# Recalcular a complexidade ignorando o valor corrompido do CSV
df['Initial_Complexity'] = df['Initial_LOC'] / df['Initial_Methods']
df['Initial_Complexity'] = df['Initial_Complexity'].fillna(0.0)

metrics = ['Initial_LOC', 'Initial_Complexity', 'CSB']
X = df[metrics].values

# Normalização Min-Max
X_min = X.min(axis=0)
X_max = X.max(axis=0)
X_norm = (X - X_min) / (X_max - X_min)

def k_means_wcss(data, k, max_iters=100, seed=42):
    np.random.seed(seed)
    initial_indices = np.random.choice(data.shape[0], k, replace=False)
    centroids = data[initial_indices]
    
    for _ in range(max_iters):
        distances = np.linalg.norm(data[:, np.newaxis] - centroids, axis=2)
        labels = np.argmin(distances, axis=1)
        
        new_centroids = np.array([
            data[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
            for i in range(k)
        ])
        
        if np.allclose(centroids, new_centroids):
            break
        centroids = new_centroids
        
    # Calcular WCSS conforme a fórmula (soma das distâncias ao quadrado)
    wcss = 0
    for i in range(k):
        if np.any(labels == i):
            cluster_points = data[labels == i]
            wcss += np.sum((cluster_points - centroids[i]) ** 2)
            
    return wcss

print("Calculando WCSS para k de 1 a 10...")
wcss_values = []
k_values = range(1, 11)

for k in k_values:
    wcss = k_means_wcss(X_norm, k)
    wcss_values.append(wcss)
    print(f"K={k}, WCSS={wcss:.4f}")

# Plotar o gráfico do Elbow Method
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.figure(figsize=(8, 6))
plt.plot(k_values, wcss_values, marker='o', linestyle='-', color='b', linewidth=2, markersize=8)
plt.title('Método do Cotovelo (Elbow Method)')
plt.xlabel('Número de Clusters (K)')
plt.ylabel('WCSS (Within-Cluster Sum of Squares)')
plt.xticks(k_values)
plt.grid(True)

# Destacar K=3 (valor atual) se for próximo ao cotovelo
plt.axvline(x=3, color='r', linestyle='--', label='K atual (3)', alpha=0.7)
plt.legend()

save_path = os.path.join(out_dir, "elbow_method.png")
plt.savefig(save_path, bbox_inches='tight', dpi=300)
print(f"Gráfico salvo em: {save_path}")

# Adicionar os valores WCSS no gráfico e salvar como novo arquivo
for i, wcss in enumerate(wcss_values):
    plt.annotate(f"{wcss:.2f}", (k_values[i], wcss_values[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='darkblue')

save_path_values = os.path.join(out_dir, "elbow_method_with_values.png")
plt.savefig(save_path_values, bbox_inches='tight', dpi=300)
print(f"Gráfico com valores salvo em: {save_path_values}")
