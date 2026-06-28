"""
Contagem de BOM por Feature ao longo das Releases do EclipseIDE.

Gera gráfico de linha do tempo com a contagem de métodos nascidos (BOM)
de cada feature ao longo de todas as versões. Cada feature é uma linha no gráfico.
Saída em PDF para uso em artigos acadêmicos.
"""

import pandas as pd
import os
import glob
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings

warnings.filterwarnings('ignore')

# ── Caminhos ──────────────────────────────────────────────────────────────────
base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, r"3-Mapeamento_features_simrel\simrel_mapper\output")
csv_dir  = os.path.join(base_dir, r"2-JMethodsExtractor\target\results")
out_dir  = os.path.join(base_dir, r"6-Analises\1-Sistema_completo_features\BOM_contagem")

os.makedirs(out_dir, exist_ok=True)

# ── Estilo acadêmico (matplotlib puro) ───────────────────────────────────────
plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],
    'font.size':          9,
    'axes.titlesize':     10,
    'axes.labelsize':     9,
    'xtick.labelsize':    7,
    'ytick.labelsize':    8,
    'legend.fontsize':    7,
    'figure.dpi':         300,
    'savefig.dpi':        300,
    'savefig.bbox':       'tight',
    'axes.grid':          True,
    'grid.alpha':         0.3,
    'grid.linewidth':     0.5,
    'axes.linewidth':     0.6,
    'lines.linewidth':    1.0,
    'lines.markersize':   3,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'pdf.fonttype':       42,
    'ps.fonttype':        42,
})

# ── 1. Carregar Linha do Tempo (Releases) ────────────────────────────────────
print("Carregando timeline de releases...")

def load_timeline():
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    timeline_data = []
    release_dates = {}
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            release_name = data.get('release')
            release_date = data.get('date')
            release_dates[release_name] = (
                pd.to_datetime(release_date, utc=True) if release_date
                else pd.Timestamp.min
            )
            for feature in data.get('mappings', {}):
                timeline_data.append({
                    'release': release_name,
                    'feature': feature
                })
    df = pd.DataFrame(timeline_data)
    if not df.empty:
        df['date'] = df['release'].map(release_dates)
        df = df.sort_values(by='date').drop_duplicates('release').reset_index(drop=True)
    return df, release_dates

df_timeline, release_dates = load_timeline()
release_order = df_timeline['release'].tolist() if not df_timeline.empty else []

if not release_order:
    print("Nenhuma release encontrada.")
    exit()

print(f"  {len(release_order)} releases encontradas.")

# ── 2. Carregar dados evolutivos (CSVs) ──────────────────────────────────────
print("Carregando CSVs de histórico de features...")
all_features_data = []
available_features = [f for f in os.listdir(csv_dir) if f.endswith("_history.csv")]

for feat_file in available_features:
    csv_file = os.path.join(csv_dir, feat_file)
    try:
        df = pd.read_csv(csv_file, low_memory=False)
        df['feature'] = feat_file.replace("_history.csv", "")
        df['BOM'] = pd.to_numeric(df['BOM'], errors='coerce').fillna(0)
        df['commit_index'] = pd.to_numeric(df['commit_index'], errors='coerce').fillna(0)
        df['LOC'] = pd.to_numeric(df['LOC'], errors='coerce').fillna(0)
        all_features_data.append(df)
    except Exception as e:
        print(f"  Erro lendo {feat_file}: {e}")

if not all_features_data:
    print("Nenhum dado evolutivo encontrado.")
    exit()

df_all = pd.concat(all_features_data, ignore_index=True)
df_all['global_method_id'] = df_all['feature'] + "_" + df_all['methodId'].astype(str)

print(f"  {len(available_features)} features carregadas, {len(df_all)} registros totais.")

# ── 3. Processar Evolução (BOM por release) ──────────────────────────────────
print("Processando evolução...")
feat_names = df_all['feature'].unique()
feature_metrics = []

groups = df_all.groupby('release', sort=False)

for r in release_order:
    if r in groups.groups:
        df_r = groups.get_group(r)
        # Identificar métodos que nasceram nesta release
        # Um método nasce num commit se o seu BOM (que guarda o index do commit de nascimento) for igual ao commit_index da linha
        born_methods = df_r[df_r['BOM'] == df_r['commit_index']].drop_duplicates('global_method_id')
        
        for feat in feat_names:
            df_feat_born = born_methods[born_methods['feature'] == feat]
            bom_count = len(df_feat_born)
            feature_metrics.append({
                'release': r,
                'feature': feat,
                'BOM Count': bom_count,
            })
    else:
        for feat in feat_names:
            feature_metrics.append({
                'release': r,
                'feature': feat,
                'BOM Count': 0,
            })

df_metrics = pd.DataFrame(feature_metrics)

# Calcular BOM Count Normalizado (0-100) por feature
df_metrics['Normalized BOM Count'] = df_metrics.groupby('feature')['BOM Count'].transform(
    lambda x: ((x - x.min()) / (x.max() - x.min())) * 100 if x.max() > x.min() else 0.0
)

# ── 4. Separar features grandes e pequenas ───────────────────────────────────
# Usando LOC total para consistência com análises anteriores
current_state_check = {feat: {} for feat in feat_names}
feature_initial_loc = {}
for r in release_order:
    if r in groups.groups:
        df_r = groups.get_group(r)
        last_states = df_r.drop_duplicates('global_method_id', keep='last')
        for feat in feat_names:
            df_feat = last_states[last_states['feature'] == feat]
            if not df_feat.empty:
                updates = df_feat.set_index('global_method_id')[['LOC']].to_dict('index')
                current_state_check[feat].update(updates)
    if r == release_order[0]:
        for feat in feat_names:
            active_locs = [v['LOC'] for v in current_state_check[feat].values() if v['LOC'] > 0]
            feature_initial_loc[feat] = int(np.sum(active_locs)) if active_locs else 0

THRESHOLD = 500_000
large_features = sorted([f for f, loc in feature_initial_loc.items() if loc > THRESHOLD])
small_features = sorted([f for f, loc in feature_initial_loc.items() if loc <= THRESHOLD])

print(f"  {len(large_features)} features grandes (>{THRESHOLD//1000}k LOC)")
print(f"  {len(small_features)} features pequenas (<={THRESHOLD//1000}k LOC)")

# ── 5. Funções de plotagem ────────────────────────────────────────────────────
def _get_palette(n):
    if n <= 10:
        cmap = matplotlib.colormaps['tab10'].resampled(10)
    elif n <= 20:
        cmap = matplotlib.colormaps['tab20'].resampled(20)
    else:
        cmap = matplotlib.colormaps['turbo'].resampled(n)
    return [cmap(i) for i in range(n)]

def plot_bom_count(df_sub, features_list, title_suffix, filename, yscale='linear'):
    n = len(features_list)
    colors = _get_palette(n)

    fig, ax = plt.subplots(figsize=(7.16, 4.0))

    x_indices = list(range(len(release_order)))

    for i, feat in enumerate(features_list):
        feat_data = df_sub[df_sub['feature'] == feat].set_index('release')
        y_vals = [feat_data.loc[r, 'BOM Count'] if r in feat_data.index else np.nan
                  for r in release_order]

        ax.plot(x_indices, y_vals,
                label=feat,
                color=colors[i],
                linewidth=1.0,
                alpha=0.85)

    ax.set_xlabel('Release')
    ax.set_ylabel('Number of Methods Born (BOM)')
    ax.set_title(f'Methods Born per Feature Over Releases {title_suffix}')

    if yscale == 'log':
        ax.set_yscale('symlog', linthresh=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f'{x/1e6:.1f}M' if abs(x) >= 1e6
            else f'{x/1e3:.0f}k' if abs(x) >= 1e3
            else f'{x:.0f}'))
    else:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f'{x/1e6:.1f}M' if abs(x) >= 1e6
            else f'{x/1e3:.0f}k' if abs(x) >= 1e3
            else f'{x:.0f}'))

    ax.set_xticks(x_indices)
    ax.set_xticklabels(release_order, rotation=90, ha='center')

    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderaxespad=0, frameon=True, fancybox=False,
              edgecolor='#cccccc', ncol=1)

    ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
    fig.tight_layout()

    save_path = os.path.join(out_dir, filename)
    fig.savefig(save_path, format='pdf', bbox_inches='tight')
    plt.close(fig)
    print(f"  Salvo: {save_path}")

def plot_normalized(df_sub, features_list, title_suffix, filename):
    n = len(features_list)
    colors = _get_palette(n)

    fig, ax = plt.subplots(figsize=(7.16, 4.0))

    x_indices = list(range(len(release_order)))

    for i, feat in enumerate(features_list):
        feat_data = df_sub[df_sub['feature'] == feat].set_index('release')
        y_vals = [feat_data.loc[r, 'Normalized BOM Count'] if r in feat_data.index else np.nan
                  for r in release_order]

        ax.plot(x_indices, y_vals,
                label=feat,
                color=colors[i],
                linewidth=1.0,
                alpha=0.85)

    ax.set_xlabel('Release')
    ax.set_ylabel('Normalized BOM Count (0-100)')
    ax.set_title(f'Normalized Methods Born per Feature Over Releases {title_suffix}')

    ax.set_ylim(-5, 105)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))

    ax.set_xticks(x_indices)
    ax.set_xticklabels(release_order, rotation=90, ha='center')

    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderaxespad=0, frameon=True, fancybox=False,
              edgecolor='#cccccc', ncol=1)

    ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
    fig.tight_layout()

    save_path = os.path.join(out_dir, filename)
    fig.savefig(save_path, format='pdf', bbox_inches='tight')
    plt.close(fig)
    print(f"  Salvo: {save_path}")


# ── 6. Gerar todos os graficos ───────────────────────────────────────────────
print("\nGerando graficos...")

# Todas as features -- absoluto
plot_bom_count(df_metrics, sorted(feat_names),
               '(All Features)', 'bom_count_all_features.pdf')

# Todas as features -- escala log
plot_bom_count(df_metrics, sorted(feat_names),
               '(All Features — Log Scale)', 'bom_count_all_features_log.pdf', yscale='log')

# Todas as features -- normalizado
plot_normalized(df_metrics, sorted(feat_names),
                '(All Features)', 'bom_count_all_features_normalized.pdf')

# Features grandes -- absoluto e normalizado
if large_features:
    df_large = df_metrics[df_metrics['feature'].isin(large_features)]
    plot_bom_count(df_large, large_features,
                   '(Large Features)', 'bom_count_large_features.pdf')
    plot_bom_count(df_large, large_features,
                   '(Large Features — Log Scale)', 'bom_count_large_features_log.pdf', yscale='log')
    plot_normalized(df_large, large_features,
                    '(Large Features)', 'bom_count_large_features_normalized.pdf')

# Features pequenas -- absoluto e normalizado
if small_features:
    df_small = df_metrics[df_metrics['feature'].isin(small_features)]
    plot_bom_count(df_small, small_features,
                   '(Small Features)', 'bom_count_small_features.pdf')
    plot_bom_count(df_small, small_features,
                   '(Small Features — Log Scale)', 'bom_count_small_features_log.pdf', yscale='log')
    plot_normalized(df_small, small_features,
                    '(Small Features)', 'bom_count_small_features_normalized.pdf')

# Exportar dados processados para CSV
csv_out = os.path.join(out_dir, 'bom_count_per_feature.csv')
df_metrics.to_csv(csv_out, index=False)
print(f"  Dados exportados: {csv_out}")

print("\nConcluido!")
