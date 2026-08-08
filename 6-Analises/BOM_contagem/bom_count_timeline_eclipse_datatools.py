import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ── Caminhos ──────────────────────────────────────────────────────────────────
base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
out_dir  = os.path.join(base_dir, r"6-Analises\1-Sistema_completo_features\BOM_contagem")
csv_in = os.path.join(out_dir, 'bom_count_per_feature.csv')

# ── Estilo acadêmico (matplotlib puro) ───────────────────────────────────────
plt.rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],
    'font.size':          9,
    'axes.titlesize':     10,
    'axes.labelsize':     10,  # Aumentado em 1 (era 9)
    'xtick.labelsize':    8,   # Aumentado em 1 (era 7)
    'ytick.labelsize':    9,   # Aumentado em 1 (era 8)
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

def _get_palette(n):
    if n <= 10:
        cmap = matplotlib.colormaps['tab10'].resampled(10)
    elif n <= 20:
        cmap = matplotlib.colormaps['tab20'].resampled(20)
    else:
        cmap = matplotlib.colormaps['turbo'].resampled(n)
    return [cmap(i) for i in range(n)]

def plot_bom_count(df_sub, features_list, filename, release_order, yscale='linear'):
    n = len(features_list)
    colors = _get_palette(n)

    # Reduzindo a altura em 3px (3/300 polegadas = 0.01). O original era (12.0, 4.0)
    fig, ax = plt.subplots(figsize=(12.0, 3))

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
    ax.set_ylabel('Métodos Nascidos (BOM)')

    if yscale == 'log':
        ax.set_yscale('symlog', linthresh=10)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f'{x/1e6:.1f}M' if abs(x) >= 1e6
            else f'{x/1e3:.0f}k' if abs(x) >= 1e3
            else f'{x:.0f}'))

    truncated_labels = [label[:14] + '...' if len(label) > 17 else label for label in release_order]
    ax.set_xticks(x_indices)
    ax.set_xticklabels(truncated_labels, rotation=45, ha='right')

    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0),
              borderaxespad=0, frameon=True, fancybox=False,
              edgecolor='#cccccc', ncol=1)

    ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
    fig.tight_layout()

    save_path = os.path.join(out_dir, filename)
    fig.savefig(save_path, format='pdf', bbox_inches='tight')
    plt.close(fig)
    print(f"  Salvo: {save_path}")

def main():
    if not os.path.exists(csv_in):
        print("Arquivo de dados base não encontrado. Execute o script principal primeiro.")
        return

    print("Lendo dados processados...")
    df_metrics = pd.read_csv(csv_in)
    
    # Mantém a ordem original das releases encontradas no dataframe
    release_order = df_metrics['release'].drop_duplicates().tolist()

    specific_features = [f for f in ['EclipseLink', 'DataTools'] if f in df_metrics['feature'].unique()]
    if specific_features:
        print("Gerando gráfico específico para EclipseLink e DataTools...")
        df_specific = df_metrics[df_metrics['feature'].isin(specific_features)]
        plot_bom_count(df_specific, specific_features,
                       'bom_count_large_features_log_EclipseLink_DataTools.pdf', 
                       release_order, yscale='log')
        print("\nConcluído!")
    else:
        print("As features EclipseLink e DataTools não foram encontradas nos dados.")

if __name__ == '__main__':
    main()
