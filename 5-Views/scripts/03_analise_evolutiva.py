import pandas as pd
import os
import glob
import json
import numpy as np
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['figure.figsize'] = (14, 12)
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'serif'

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, r"3-Mapeamento_features_simrel\simrel_mapper\output")
csv_dir = os.path.join(base_dir, r"2-JMethodsExtractor\target\results")
out_dir = os.path.join(base_dir, r"5-Views\resultados\03_analise_evolutiva\timeline_loc")

os.makedirs(out_dir, exist_ok=True)

print("Iniciando geração de gráficos evolutivos...")

# 1. Carregar Linha do Tempo (Releases)
def load_timeline():
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    timeline_data = []
    release_dates = {}
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            release_name = data.get('release')
            release_date = data.get('date')
            release_dates[release_name] = pd.to_datetime(release_date, utc=True) if release_date else pd.Timestamp.min
            for feature, feature_data in data.get('mappings', {}).items():
                timeline_data.append({
                    'release': release_name,
                    'feature': feature
                })
    df_timeline = pd.DataFrame(timeline_data)
    if not df_timeline.empty:
        df_timeline['date'] = df_timeline['release'].map(release_dates)
        df_timeline = df_timeline.sort_values(by='date').drop_duplicates('release').reset_index(drop=True)
    return df_timeline

df_timeline = load_timeline()
release_order = df_timeline['release'].tolist() if not df_timeline.empty else []

if not release_order:
    print("Nenhuma release encontrada nos JSONs.")
    exit()

# 2. Carregar todos os dados evolutivos
all_features_data = []
available_features = [f for f in os.listdir(csv_dir) if f.endswith("_history.csv")]

print(f"Lendo {len(available_features)} arquivos CSV de histórico...")
for feat_file in available_features:
    csv_file = os.path.join(csv_dir, feat_file)
    try:
        df = pd.read_csv(csv_file, low_memory=False)
        df['feature'] = feat_file.replace("_history.csv", "")
        all_features_data.append(df)
    except Exception as e:
        print(f"Erro lendo {feat_file}: {e}")

if not all_features_data:
    print("Nenhum dado evolutivo encontrado.")
    exit()

df_all = pd.concat(all_features_data, ignore_index=True)

# Criar ID global para métodos (FeatureName + MethodId) para evitar colisões
df_all['global_method_id'] = df_all['feature'] + "_" + df_all['methodId'].astype(str)

# 3. Processar Evolução (Por Feature)
print("Processando histórico e simulando estado global de métodos por feature...")
current_state_feat = {}
feature_metrics = []

feat_names = df_all['feature'].unique()
for feat in feat_names:
    current_state_feat[feat] = {}

groups = df_all.groupby('release', sort=False)

for r in release_order:
    if r in groups.groups:
        df_r = groups.get_group(r)
        last_states = df_r.drop_duplicates('global_method_id', keep='last')
        
        for feat in feat_names:
            df_feat = last_states[last_states['feature'] == feat]
            if not df_feat.empty:
                updates = df_feat.set_index('global_method_id')[['LOC']].to_dict('index')
                current_state_feat[feat].update(updates)
                
    for feat in feat_names:
        active_locs = [v['LOC'] for v in current_state_feat[feat].values() if v['LOC'] > 0]
        
        if active_locs:
            total_loc = np.sum(active_locs)
            mean_loc = np.mean(active_locs)
            median_loc = np.median(active_locs)
        else:
            total_loc = 0
            mean_loc = 0
            median_loc = 0
            
        feature_metrics.append({
            'release': r,
            'feature': feat,
            'Total LOC': total_loc,
            'Mean LOC': mean_loc,
            'Median LOC': median_loc
        })

df_metrics = pd.DataFrame(feature_metrics)

# Calcular LOC Normalizado (0-100) por feature
df_metrics['Normalized LOC'] = df_metrics.groupby('feature')['Total LOC'].transform(
    lambda x: ((x - x.min()) / (x.max() - x.min())) * 100 if x.max() > x.min() else 0.0
)
df_metrics['Normalized Mean LOC'] = df_metrics.groupby('feature')['Mean LOC'].transform(
    lambda x: ((x - x.min()) / (x.max() - x.min())) * 100 if x.max() > x.min() else 0.0
)

# Identificar Features Grandes e Pequenas (Critério: LOC total na primeira release presente > 500k)
feature_initial_loc = {}
for feat in df_metrics['feature'].unique():
    feat_data = df_metrics[df_metrics['feature'] == feat]
    initial_loc = feat_data.iloc[0]['Total LOC']
    feature_initial_loc[feat] = initial_loc

large_features = [f for f, loc in feature_initial_loc.items() if loc > 500000]
small_features = [f for f, loc in feature_initial_loc.items() if loc <= 500000]

print(f"\nDividindo Features: {len(large_features)} grandes (>500k LOC) e {len(small_features)} pequenas (<=500k LOC)")

# 4. Plotagem
def plot_subset(df_subset, subset_name, filename_suffix, scale='linear', log_norm=False):
    if df_subset.empty: return
    subset_features = df_subset['feature'].unique()
    
    print(f"Gerando gráficos para a categoria {subset_name} (Scale: {scale}, LogNorm: {log_norm})...")
    fig, axes = plt.subplots(5, 1, sharex=True, figsize=(14, 28))
    
    palette = sns.color_palette("tab20", n_colors=len(subset_features))
    
    # Se log_norm for True, recalcula a normalização baseada no logaritmo
    if log_norm:
        df_subset['Log Total LOC'] = np.log1p(df_subset['Total LOC'])
        df_subset['Normalized LOC'] = df_subset.groupby('feature')['Log Total LOC'].transform(
            lambda x: ((x - x.min()) / (x.max() - x.min())) * 100 if x.max() > x.min() else 0.0
        )
        df_subset['Log Mean LOC'] = np.log1p(df_subset['Mean LOC'])
        df_subset['Normalized Mean LOC'] = df_subset.groupby('feature')['Log Mean LOC'].transform(
            lambda x: ((x - x.min()) / (x.max() - x.min())) * 100 if x.max() > x.min() else 0.0
        )
    
    # Subplot 1: Total LOC
    sns.lineplot(data=df_subset, x='release', y='Total LOC', hue='feature', ax=axes[0], marker='o', palette=palette, linewidth=1.5)
    axes[0].set_title(f'Total de LOC por Feature {subset_name}', fontsize=14)
    axes[0].set_ylabel('Total LOC')
    axes[0].legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize='small')
    
    # Subplot 2: Normalized LOC
    sns.lineplot(data=df_subset, x='release', y='Normalized LOC', hue='feature', ax=axes[1], marker='d', palette=palette, linewidth=1.5, legend=False)
    axes[1].set_title(f'LOC Normalizado (0-100) por Feature {subset_name}' + (' [Base Log]' if log_norm else ''), fontsize=14)
    axes[1].set_ylabel('LOC Normalizado')
    
    # Subplot 3: Mean LOC
    sns.lineplot(data=df_subset, x='release', y='Mean LOC', hue='feature', ax=axes[2], marker='s', palette=palette, linewidth=1.5, legend=False)
    axes[2].set_title(f'Média de LOC por Método Ativo {subset_name}', fontsize=14)
    axes[2].set_ylabel('Média')
    
    # Subplot 4: Normalized Mean LOC
    sns.lineplot(data=df_subset, x='release', y='Normalized Mean LOC', hue='feature', ax=axes[3], marker='s', palette=palette, linewidth=1.5, legend=False)
    axes[3].set_title(f'Média de LOC Normalizada (0-100) por Método Ativo {subset_name}' + (' [Base Log]' if log_norm else ''), fontsize=14)
    axes[3].set_ylabel('Média Normalizada')
    
    # Subplot 5: Median LOC
    sns.lineplot(data=df_subset, x='release', y='Median LOC', hue='feature', ax=axes[4], marker='^', palette=palette, linewidth=1.5, legend=False)
    axes[4].set_title(f'Mediana de LOC por Método Ativo {subset_name}', fontsize=14)
    axes[4].set_ylabel('Mediana')
    
    if scale == 'log':
        axes[0].set_yscale('symlog')
        axes[2].set_yscale('symlog')
        axes[4].set_yscale('symlog')
        if not log_norm:
            axes[1].set_yscale('symlog')
            axes[3].set_yscale('symlog')
    
    # Formatando Eixo X
    axes[4].set_xticks(range(len(release_order)))
    axes[4].set_xticklabels(release_order, rotation=90)
    axes[4].set_xlabel('Release', fontsize=12)
    
    for ax in axes:
        ax.grid(True, linestyle='--', alpha=0.7)
        
    plt.tight_layout()
    
    suffix = filename_suffix
    if scale == 'log':
        suffix += "_log"
    if log_norm:
        suffix += "_norm"
        
    save_path = os.path.join(out_dir, f"loc_system_evolution{suffix}.pdf")
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    
    print(f"Salvo em: {save_path}")

plot_subset(df_metrics.copy(), "(Todas as Features)", "")
plot_subset(df_metrics.copy(), "(Todas as Features)", "", scale='log')
plot_subset(df_metrics.copy(), "(Todas as Features)", "", scale='log', log_norm=True)

if large_features:
    plot_subset(df_metrics[df_metrics['feature'].isin(large_features)].copy(), "(Grandes: Início > 500k LOC)", "_grandes")
    plot_subset(df_metrics[df_metrics['feature'].isin(large_features)].copy(), "(Grandes: Início > 500k LOC)", "_grandes", scale='log')
    plot_subset(df_metrics[df_metrics['feature'].isin(large_features)].copy(), "(Grandes: Início > 500k LOC)", "_grandes", scale='log', log_norm=True)

if small_features:
    plot_subset(df_metrics[df_metrics['feature'].isin(small_features)].copy(), "(Pequenas: Início <= 500k LOC)", "_pequenas")
    plot_subset(df_metrics[df_metrics['feature'].isin(small_features)].copy(), "(Pequenas: Início <= 500k LOC)", "_pequenas", scale='log')
    plot_subset(df_metrics[df_metrics['feature'].isin(small_features)].copy(), "(Pequenas: Início <= 500k LOC)", "_pequenas", scale='log', log_norm=True)

