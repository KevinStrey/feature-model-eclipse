import pandas as pd
import numpy as np
import os
import glob
import json
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['savefig.dpi'] = 300

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, r"3-Mapeamento_features_simrel\simrel_mapper\output")
csv_dir = os.path.join(base_dir, r"2-JMethodsExtractor\target\results")
out_dir = os.path.join(base_dir, r"5-Views\resultados\01_extracao_base")

for sub in ['tamanho', 'complexidade', 'mudanca', 'grupos']:
    os.makedirs(os.path.join(out_dir, sub), exist_ok=True)

print("Iniciando a Classificação e Análise de Features...")

# 1. Carregar Linha do Tempo
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
                timeline_data.append({'release': release_name, 'feature': feature})
    df_timeline = pd.DataFrame(timeline_data)
    if not df_timeline.empty:
        df_timeline['date'] = df_timeline['release'].map(release_dates)
        df_timeline = df_timeline.sort_values(by='date').drop_duplicates('release').reset_index(drop=True)
    return df_timeline

df_timeline = load_timeline()
release_order = df_timeline['release'].tolist() if not df_timeline.empty else []

# 2. Carregar Dados Evolutivos
all_features_data = []
available_features = [f for f in os.listdir(csv_dir) if f.endswith("_history.csv")]
print(f"Carregando {len(available_features)} features...")
for feat_file in available_features:
    csv_file = os.path.join(csv_dir, feat_file)
    df = pd.read_csv(csv_file, low_memory=False)
    df['feature'] = feat_file.replace("_history.csv", "")
    all_features_data.append(df)

df_all = pd.concat(all_features_data, ignore_index=True)
df_all['global_method_id'] = df_all['feature'] + "_" + df_all['methodId'].astype(str)

# Tratar possíveis strings com vírgula no lugar de ponto
evol_metrics = ["BOM","TACH","CHD","FCH","LCH","FRCH","WCH","WCD","CSB","CSBS","ACDF","LOC"]
for col in evol_metrics:
    if col in df_all.columns:
        # Força conversão para string, substitui vírgula e converte para float independente do tipo lido pelo pandas
        df_all[col] = df_all[col].astype(str).str.replace(',', '.').astype(float)

# 3. Calcular Eixos por Feature
print("Processando acumulações e deltas evolutivos...")
# As métricas como CSB e LCH são cumulativas. Para obter o total de uma feature, extraímos o valor máximo alcançado por cada método e somamos.
methods_max = df_all.groupby(['feature', 'global_method_id'])[evol_metrics].max().reset_index()
feature_evol_sum = methods_max.groupby('feature')[evol_metrics].sum()

feature_stats = []
groups = df_all.groupby('release', sort=False)

feat_names = df_all['feature'].unique()
current_state_feat = {f: {} for f in feat_names}
feature_timeline_states = {f: {} for f in feat_names}

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
            feature_timeline_states[feat][r] = {
                'LOC': np.sum(active_locs),
                'Methods': len(active_locs),
                'Complexity': np.mean(active_locs)
            }

for feat, states in feature_timeline_states.items():
    if not states: continue
    releases_present = list(states.keys())
    first_r = releases_present[0]
    last_r = releases_present[-1]
    
    init_loc = states[first_r]['LOC']
    init_methods = states[first_r]['Methods']
    init_cx = states[first_r]['Complexity']
    
    final_loc = states[last_r]['LOC']
    final_methods = states[last_r]['Methods']
    final_cx = states[last_r]['Complexity']
    
    delta_loc = final_loc - init_loc
    delta_methods = final_methods - init_methods
    
    feat_data = {
        'feature': feat,
        'Initial_LOC': init_loc,
        'Initial_Methods': init_methods,
        'Initial_Complexity': init_cx,
        'Final_LOC': final_loc,
        'Final_Methods': final_methods,
        'Final_Complexity': final_cx,
        'Delta_LOC': delta_loc,
        'Delta_Methods': delta_methods,
        'Relative_Delta_LOC': (delta_loc / init_loc * 100) if init_loc > 0 else 0
    }
    feature_stats.append(feat_data)

df_stats = pd.DataFrame(feature_stats).set_index('feature')
df_final = df_stats.join(feature_evol_sum)

# 4. Classificação (Quartis 25% / 50% / 75%)
print("Classificando features em categorias...")
def classify_quartile(series):
    try:
        return pd.qcut(series, q=4, labels=['Baixo', 'Médio-Baixo', 'Médio-Alto', 'Alto'], duplicates='drop')
    except:
        return series

df_final['Classe_Tamanho_LOC'] = classify_quartile(df_final['Initial_LOC'])
df_final['Classe_Complexidade'] = classify_quartile(df_final['Initial_Complexity'])
df_final['Classe_Mudanca_LCH'] = classify_quartile(df_final['LCH'])
df_final['Classe_Mudanca_DeltaLOC'] = classify_quartile(df_final['Delta_LOC'])

# Salvar dados tabulares
df_final.to_csv(os.path.join(out_dir, "classificacao_features.csv"))

# 5. Gerar Gráficos
print("Gerando gráficos...")

# A) TAMANHO
plt.figure(figsize=(12, 8))
sns.scatterplot(data=df_final, x='Initial_LOC', y='Initial_Methods', hue='Classe_Tamanho_LOC', size='Final_Complexity', sizes=(50, 400), alpha=0.7)
plt.title('Tamanho Inicial: LOC vs Quantidade de Métodos\n(Tamanho da bolha = Complexidade LOC/Método)')
plt.xlabel('LOC Inicial Total')
plt.ylabel('Qtd Métodos Inicial')
for i, txt in enumerate(df_final.index):
    plt.annotate(txt, (df_final['Initial_LOC'].iloc[i], df_final['Initial_Methods'].iloc[i]), fontsize=8, alpha=0.8)
plt.savefig(os.path.join(out_dir, 'tamanho', 'scatter_loc_vs_methods.pdf'), bbox_inches='tight')
plt.close()

# B) COMPLEXIDADE
plt.figure(figsize=(10, 6))
sns.boxplot(data=df_final, x='Classe_Complexidade', y='Initial_Complexity', order=['Baixo', 'Médio-Baixo', 'Médio-Alto', 'Alto'])
plt.title('Distribuição de Complexidade (LOC/Método) por Classe')
plt.ylabel('Complexidade Inicial (Média de LOC por Método)')
plt.savefig(os.path.join(out_dir, 'complexidade', 'boxplot_complexidade.pdf'), bbox_inches='tight')
plt.close()

plt.figure(figsize=(14, 7))
df_sorted = df_final.sort_values('Initial_Complexity', ascending=False)
sns.barplot(data=df_sorted, x=df_sorted.index, y='Initial_Complexity', hue='Classe_Complexidade', dodge=False)
plt.xticks(rotation=90)
plt.title('Ranking de Complexidade Inicial por Feature')
plt.ylabel('LOC / Método')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'complexidade', 'ranking_complexidade.pdf'), bbox_inches='tight')
plt.close()

# C) MUDANÇA
plt.figure(figsize=(12, 8))
sns.scatterplot(data=df_final, x='Initial_LOC', y='LCH', hue='Classe_Mudanca_LCH', size='CSB', sizes=(50, 500), alpha=0.7)
plt.title('Esforço Evolutivo: Tamanho Inicial vs Linhas Alteradas (LCH)\n(Tamanho da bolha = Quantidade de Commits CSB)')
plt.xlabel('LOC Inicial')
plt.ylabel('Total Acumulado de Linhas Alteradas (LCH)')
for i, txt in enumerate(df_final.index):
    plt.annotate(txt, (df_final['Initial_LOC'].iloc[i], df_final['LCH'].iloc[i]), fontsize=8, alpha=0.8)
plt.savefig(os.path.join(out_dir, 'mudanca', 'scatter_tamanho_vs_mudanca.pdf'), bbox_inches='tight')
plt.close()

# D) CORRELAÇÃO MÚLTIPLA
plt.figure(figsize=(14, 12))
corr = df_final[['Initial_LOC', 'Initial_Methods', 'Initial_Complexity', 'Delta_LOC', 'Delta_Methods', 'BOM', 'LCH', 'FRCH', 'CSB', 'ACDF']].corr()
sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", square=True, linewidths=.5)
plt.title('Matriz de Correlação Global (Características Iniciais vs Evolutivas)')
plt.savefig(os.path.join(out_dir, 'mudanca', 'heatmap_global.pdf'), bbox_inches='tight')
plt.close()

# E) PAIRPLOT (Visão Geral de Grupos)
subset = df_final[['Initial_LOC', 'Initial_Complexity', 'LCH', 'Delta_LOC', 'Classe_Tamanho_LOC']]
sns.pairplot(subset, hue='Classe_Tamanho_LOC', corner=True, palette='tab10')
plt.savefig(os.path.join(out_dir, 'grupos', 'pairplot_multivariado.pdf'), bbox_inches='tight')
plt.close()

print(f"Análise Concluída! Gráficos salvos em: {out_dir}")
