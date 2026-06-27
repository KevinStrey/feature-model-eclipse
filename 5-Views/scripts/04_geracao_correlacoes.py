import pandas as pd
import os
import glob
import json
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'serif'

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, r"3-Mapeamento_features_simrel\simrel_mapper\output")
csv_dir = os.path.join(base_dir, r"2-JMethodsExtractor\target\results")
ck_csv_dir = os.path.join(base_dir, r"4-CKHistoryExtractor\target\results")
out_dir = os.path.join(base_dir, r"5-Views\resultados\04_correlacoes")

# Create folders
for sub in ["ck", "evol", "ck_vs_evol"]:
    os.makedirs(os.path.join(out_dir, sub, "matrizes"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, sub, "radars"), exist_ok=True)

ck_metrics_list = [
    "cbo","cboModified","fanin","fanout","wmc","rfc","loc","returnsQty",
    "variablesQty","parametersQty","methodsInvokedQty","methodsInvokedLocalQty",
    "methodsInvokedIndirectLocalQty","loopQty","comparisonsQty","tryCatchQty",
    "parenthesizedExpsQty","stringLiteralsQty","numbersQty","assignmentsQty",
    "mathOperationsQty","maxNestedBlocksQty","anonymousClassesQty","innerClassesQty",
    "lambdasQty","uniqueWordsQty","modifiers","logStatementsQty","hasJavaDoc"
]
evol_metrics_list = ["CSB", "FRCH", "LOC_evol"]

# ======================= DATA LOADING =======================
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
                    'feature': feature,
                    'commit': feature_data.get('commit'),
                    'status': feature_data.get('status')
                })
    df_timeline = pd.DataFrame(timeline_data)
    if not df_timeline.empty:
        df_timeline['date'] = df_timeline['release'].map(release_dates)
        df_timeline = df_timeline.sort_values(by='date').drop(columns=['date']).reset_index(drop=True)
    return df_timeline

def load_feature_data(feature_name):
    csv_file = os.path.join(csv_dir, f"{feature_name}_history.csv")
    if not os.path.exists(csv_file): return None
    return pd.read_csv(csv_file)

def load_ck_data(feature_name):
    ck_file = os.path.join(ck_csv_dir, f"{feature_name}_method_history.csv")
    if not os.path.exists(ck_file): return None
    try:
        try:
            df_ck = pd.read_csv(ck_file, sep=',', on_bad_lines='skip', low_memory=False)
            if 'release' not in df_ck.columns:
                df_ck = pd.read_csv(ck_file, sep=';', on_bad_lines='skip', low_memory=False)
        except:
            df_ck = pd.read_csv(ck_file, sep=';', on_bad_lines='skip', low_memory=False)
            
        if not df_ck.empty and 'release' in df_ck.columns:
            cols_to_agg = [c for c in ck_metrics_list if c in df_ck.columns]
            for col in cols_to_agg:
                df_ck[col] = pd.to_numeric(df_ck[col], errors='coerce')
            df_ck_agg = df_ck.groupby('release', as_index=False)[cols_to_agg].mean()
            return df_ck_agg
    except Exception as e:
        print(f"Erro processando CK de {feature_name}: {e}")
    return None

df_timeline = load_timeline()
available_features = [f.replace("_history.csv", "") for f in os.listdir(csv_dir) if f.endswith("_history.csv")]

def process_evolution(df_feature, release_order):
    current_state = {}
    known_methods = set()
    feature_metrics = []
    groups = df_feature.groupby('release', sort=False)
    for r in release_order:
        if r in groups.groups:
            df_r = groups.get_group(r)
            last_states = df_r.drop_duplicates('methodId', keep='last')
            updates = last_states.set_index('methodId')[['LOC', 'CSB', 'FRCH']].to_dict('index')
            current_state.update(updates)
        active_methods = [v for v in current_state.values() if v['LOC'] > 0]
        total_active = len(active_methods)
        if total_active > 0:
            total_loc = sum(v['LOC'] for v in active_methods)
            avg_csb = sum(v['CSB'] for v in active_methods) / total_active
            avg_frch = sum(v['FRCH'] for v in active_methods) / total_active
            feature_metrics.append({
                'release': r, 'LOC_evol': total_loc, 'CSB': avg_csb, 'FRCH': avg_frch
            })
    df_agg = pd.DataFrame(feature_metrics)
    if not df_agg.empty:
        df_agg['release'] = pd.Categorical(df_agg['release'], categories=release_order, ordered=True)
        df_agg = df_agg.sort_values('release')
    return df_agg

if not df_timeline.empty:
    release_order = df_timeline['release'].unique().tolist()
else:
    release_order = []

dict_evol_agg = {}
dict_ck_agg = {}
dict_merged = {}

print("Processando dados (Carregando e agregando CSVs)...")
for feat in available_features:
    df_f = load_feature_data(feat)
    if df_f is not None and not df_f.empty and release_order:
        df_evol = process_evolution(df_f, release_order)
        if not df_evol.empty:
            dict_evol_agg[feat] = df_evol
            
    df_ck = load_ck_data(feat)
    if df_ck is not None and not df_ck.empty:
        dict_ck_agg[feat] = df_ck
        
    if feat in dict_evol_agg and feat in dict_ck_agg:
        merged = pd.merge(dict_evol_agg[feat], dict_ck_agg[feat], on='release', how='inner')
        if not merged.empty:
            dict_merged[feat] = merged

def generate_feature_radar(feat_name, corr_df, category_out_dir, is_slice=False):
    import numpy as np
    pairs_r = []
    
    if not is_slice:
        for i in range(len(corr_df.columns)):
            for j in range(i+1, len(corr_df.columns)):
                c1, c2 = corr_df.columns[i], corr_df.columns[j]
                val = corr_df.iloc[i, j]
                if pd.notna(val) and abs(val) > 0.7:
                    pair_name = f"{min(c1, c2)} vs {max(c1, c2)}"
                    pairs_r.append((pair_name, val))
    else:
        for ev_c in corr_df.index:
            for ck_c in corr_df.columns:
                val = corr_df.loc[ev_c, ck_c]
                if pd.notna(val) and abs(val) > 0.7:
                    pair_name = f"{ev_c} vs {ck_c}"
                    pairs_r.append((pair_name, val))
                    
    if not pairs_r:
        return
        
    pairs_r = sorted(pairs_r, key=lambda x: abs(x[1]), reverse=True)[:40]
    
    pair_names = [p[0] for p in pairs_r]
    pos_counts = [p[1] if p[1] > 0 else 0 for p in pairs_r]
    neg_counts = [abs(p[1]) if p[1] < 0 else 0 for p in pairs_r]
    
    N = len(pair_names)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    pos_counts += pos_counts[:1]
    neg_counts += neg_counts[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': 'polar'})
    
    plt.xticks(angles[:-1], pair_names, size=8)
    ax.tick_params(axis='x', pad=15)
    ax.set_rlabel_position(0)
    ax.set_ylim(0, 1.0)
    
    ax.plot(angles, pos_counts, linewidth=2, linestyle='solid', label='Positiva (r > 0.7)', color='steelblue')
    ax.fill(angles, pos_counts, 'steelblue', alpha=0.3)
    
    ax.plot(angles, neg_counts, linewidth=2, linestyle='solid', label='Negativa (r < -0.7)', color='indianred')
    ax.fill(angles, neg_counts, 'indianred', alpha=0.3)
    
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    plt.title(f"{feat_name} - Correlações Fortes (|r| > 0.7)", size=14, y=1.1)
    
    radar_dir = os.path.join(category_out_dir, "radars")
    plt.savefig(os.path.join(radar_dir, f"{feat_name}_radar.pdf"), bbox_inches='tight')
    plt.close()

# ======================= HISTOGRAM PLOTTING =======================
def plot_histogram(counts_dict, title, xlabel, save_path):
    if not counts_dict:
        print(f"Sem dados fortes (abs > 0.7) para {title}")
        return
        
    pairs_tie = []
    pairs_pos_majority = []
    pairs_neg_majority = []
    pairs_only_pos = []
    pairs_only_neg = []

    for pair, counts in counts_dict.items():
        pos_count = len(counts['positive'])
        neg_count = len(counts['negative'])
        if pos_count > 0 or neg_count > 0:
            diff = pos_count - neg_count
            if abs(diff) <= 1:
                pairs_tie.append(pair)
            elif diff > 1:
                pairs_pos_majority.append(pair)
            else:
                pairs_neg_majority.append(pair)
                
            if pos_count > 0 and neg_count == 0:
                pairs_only_pos.append(pair)
            elif neg_count > 0 and pos_count == 0:
                pairs_only_neg.append(pair)

    def generate_plot(pairs_subset, sub_title, suffix):
        if not pairs_subset:
            return
        
        # 1. Gráfico Simples (Azul e Vermelho)
        rows_simple = []
        for pair in pairs_subset:
            counts = counts_dict[pair]
            pos_count = len(counts['positive'])
            neg_count = len(counts['negative'])
            if pos_count > 0 or neg_count > 0:
                rows_simple.append({'Correlation': pair, 'Count': pos_count, 'Type': 'Positiva (r > 0.7)'})
                rows_simple.append({'Correlation': pair, 'Count': neg_count, 'Type': 'Negativa (r < -0.7)'})
        
        df_simple = pd.DataFrame(rows_simple)
        if not df_simple.empty:
            total_counts_simple = df_simple.groupby('Correlation')['Count'].sum().sort_values(ascending=False).index
            
            plt.figure(figsize=(max(12, len(total_counts_simple)*0.5), 14))
            sns.barplot(data=df_simple, x='Correlation', y='Count', hue='Type', palette={'Positiva (r > 0.7)': 'steelblue', 'Negativa (r < -0.7)': 'indianred'}, order=total_counts_simple)
            plt.title(f"{title} - {sub_title}")
            plt.xlabel(xlabel)
            plt.ylabel("Qtd de Features")
            plt.xticks(rotation=90)
            plt.legend(title="Tipo de Correlação")
            plt.subplots_adjust(bottom=0.45)
            
            base, ext = os.path.splitext(save_path)
            plt.savefig(f"{base}_{suffix}_simples{ext}", bbox_inches='tight')
            plt.close()

        # 2. Gráfico Colorido (Stacked Features)
        rows_features = []
        for pair in pairs_subset:
            counts = counts_dict[pair]
            for feat in counts['positive']:
                rows_features.append({'Correlation': pair, 'Type': 'Positiva', 'Feature': feat, 'Count': 1})
            for feat in counts['negative']:
                rows_features.append({'Correlation': pair, 'Type': 'Negativa', 'Feature': feat, 'Count': 1})
                
        df_counts = pd.DataFrame(rows_features)
        if df_counts.empty:
            return
            
        # Garante que Positiva venha antes de Negativa no pivot
        df_counts['Type'] = pd.Categorical(df_counts['Type'], categories=['Positiva', 'Negativa'], ordered=True)
        pivot_df = df_counts.pivot_table(index=['Correlation', 'Type'], columns='Feature', values='Count', aggfunc='sum').fillna(0)
        
        pair_totals = df_counts.groupby('Correlation')['Count'].sum().sort_values(ascending=False)
        pivot_df = pivot_df.reindex(pair_totals.index, level='Correlation')
        
        fig, ax = plt.subplots(figsize=(max(12, len(pivot_df)*0.4), 14))
        
        pivot_df.plot(kind='bar', stacked=True, ax=ax, colormap='tab20', width=0.8, edgecolor='black', linewidth=0.5)
        
        plt.title(f"{title} - {sub_title}")
        plt.xlabel(xlabel)
        plt.ylabel("Qtd de Features")
        
        labels = [f"{idx[0]}\n({idx[1]})" for idx in pivot_df.index]
        ax.set_xticklabels(labels, rotation=90, )
        
        plt.legend(title="Feature", bbox_to_anchor=(1.01, 1), loc='upper left')
        plt.subplots_adjust(bottom=0.45)
        
        base, ext = os.path.splitext(save_path)
        plt.savefig(f"{base}_{suffix}_colorido{ext}", bbox_inches='tight')
        plt.close()

    def generate_radar_plot():
        import numpy as np
        pairs = [pair for pair, counts in counts_dict.items() if len(counts['positive']) > 0 or len(counts['negative']) > 0]
        if not pairs:
            return
            
        pairs = sorted(pairs, key=lambda p: len(counts_dict[p]['positive']) + len(counts_dict[p]['negative']), reverse=True)
        # Limitar para os 40 pares mais frequentes para legibilidade do radar
        if len(pairs) > 40:
            pairs = pairs[:40]
            
        pos_counts = [len(counts_dict[pair]['positive']) for pair in pairs]
        neg_counts = [len(counts_dict[pair]['negative']) for pair in pairs]
        
        N = len(pairs)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        pos_counts += pos_counts[:1]
        neg_counts += neg_counts[:1]
        
        fig, ax = plt.subplots(figsize=(14, 14), subplot_kw={'projection': 'polar'})
        
        plt.xticks(angles[:-1], pairs, size=10)
        ax.tick_params(axis='x', pad=15)
        ax.set_rlabel_position(0)
        
        ax.plot(angles, pos_counts, linewidth=2, linestyle='solid', label='Positiva (r > 0.7)', color='steelblue')
        ax.fill(angles, pos_counts, 'steelblue', alpha=0.3)
        
        ax.plot(angles, neg_counts, linewidth=2, linestyle='solid', label='Negativa (r < -0.7)', color='indianred')
        ax.fill(angles, neg_counts, 'indianred', alpha=0.3)
        
        plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
        plt.title(f"{title} - Radar Global", size=16, y=1.1)
        
        base, ext = os.path.splitext(save_path)
        plt.savefig(f"{base}_radar{ext}", bbox_inches='tight')
        plt.close()

    generate_radar_plot()
    generate_plot(pairs_pos_majority, "Maioria Positiva", "maioria_positiva")
    generate_plot(pairs_neg_majority, "Maioria Negativa", "maioria_negativa")
    generate_plot(pairs_tie, "Empate Técnico (Dif <= 1)", "empate_tecnico")
    generate_plot(pairs_only_pos, "Somente Positivas", "somente_positivas")
    generate_plot(pairs_only_neg, "Somente Negativas", "somente_negativas")

# ======================= ANALYSIS =======================

# 1. CK vs CK
print("1. Gerando Matrizes e Histograma: CK vs CK...")
ck_corr_counts = defaultdict(lambda: {'positive': [], 'negative': []})
for feat, df in dict_ck_agg.items():
    cols = [c for c in ck_metrics_list if c in df.columns]
    if len(cols) > 1:
        corr = df[cols].corr(numeric_only=True)
        plt.figure(figsize=(24, 20))
        sns.heatmap(corr, annot=True, cmap="RdBu_r", vmin=-1, vmax=1, fmt=".1f", annot_kws={"size": 6})
        plt.title(f"{feat}: Correlação CK vs CK")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "ck", "matrizes", f"{feat}_ck_corr.pdf"))
        plt.close()
        
        generate_feature_radar(feat, corr, os.path.join(out_dir, "ck"), is_slice=False)
        
        for i in range(len(corr.columns)):
            for j in range(i+1, len(corr.columns)):
                c1, c2 = corr.columns[i], corr.columns[j]
                val = corr.iloc[i, j]
                if pd.notna(val):
                    if val > 0.7:
                        pair_name = f"{min(c1, c2)} vs {max(c1, c2)}"
                        ck_corr_counts[pair_name]['positive'].append(feat)
                    elif val < -0.7:
                        pair_name = f"{min(c1, c2)} vs {max(c1, c2)}"
                        ck_corr_counts[pair_name]['negative'].append(feat)

plot_histogram(ck_corr_counts, "Histograma: Correlações Fortes - CK vs CK", "Par de Métricas CK", os.path.join(out_dir, "ck", "histograma_ck_altos.pdf"))

# 2. Evol vs Evol
print("2. Gerando Matrizes e Histograma: Evol vs Evol...")
evol_corr_counts = defaultdict(lambda: {'positive': [], 'negative': []})
for feat, df in dict_evol_agg.items():
    cols = [c for c in evol_metrics_list if c in df.columns]
    if len(cols) > 1:
        corr = df[cols].corr(numeric_only=True)
        plt.figure(figsize=(6, 5))
        sns.heatmap(corr, annot=True, cmap="RdBu_r", vmin=-1, vmax=1, fmt=".2f")
        plt.title(f"{feat}: Correlação Evolutiva")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "evol", "matrizes", f"{feat}_evol_corr.pdf"))
        plt.close()
        
        generate_feature_radar(feat, corr, os.path.join(out_dir, "evol"), is_slice=False)
        
        for i in range(len(corr.columns)):
            for j in range(i+1, len(corr.columns)):
                c1, c2 = corr.columns[i], corr.columns[j]
                val = corr.iloc[i, j]
                if pd.notna(val):
                    if val > 0.7:
                        pair_name = f"{min(c1, c2)} vs {max(c1, c2)}"
                        evol_corr_counts[pair_name]['positive'].append(feat)
                    elif val < -0.7:
                        pair_name = f"{min(c1, c2)} vs {max(c1, c2)}"
                        evol_corr_counts[pair_name]['negative'].append(feat)

plot_histogram(evol_corr_counts, "Histograma: Correlações Fortes - Evol vs Evol", "Par de Métricas Evolutivas", os.path.join(out_dir, "evol", "histograma_evol_altos.pdf"))

# 3. Evol vs CK
print("3. Gerando Matrizes e Histograma: Evol vs CK...")
ck_evol_corr_counts = defaultdict(lambda: {'positive': [], 'negative': []})
for feat, df in dict_merged.items():
    ck_cols = [c for c in ck_metrics_list if c in df.columns]
    ev_cols = [c for c in evol_metrics_list if c in df.columns]
    if ck_cols and ev_cols:
        corr_full = df[ck_cols + ev_cols].corr(numeric_only=True)
        corr_slice = corr_full.loc[ev_cols, ck_cols]
        
        plt.figure(figsize=(24, 4))
        sns.heatmap(corr_slice, annot=True, cmap="RdBu_r", vmin=-1, vmax=1, fmt=".1f", annot_kws={"size": 8})
        plt.title(f"{feat}: Correlação Evolutiva (Y) vs CK (X)")
        plt.ylabel("Métricas Evolutivas")
        plt.xlabel("Métricas CK")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "ck_vs_evol", "matrizes", f"{feat}_ck_vs_evol_corr.pdf"))
        plt.close()
        
        generate_feature_radar(feat, corr_slice, os.path.join(out_dir, "ck_vs_evol"), is_slice=True)
        
        for ev_c in ev_cols:
            for ck_c in ck_cols:
                val = corr_slice.loc[ev_c, ck_c]
                if pd.notna(val):
                    if val > 0.7:
                        pair_name = f"{ev_c} vs {ck_c}"
                        ck_evol_corr_counts[pair_name]['positive'].append(feat)
                    elif val < -0.7:
                        pair_name = f"{ev_c} vs {ck_c}"
                        ck_evol_corr_counts[pair_name]['negative'].append(feat)

plot_histogram(ck_evol_corr_counts, "Histograma: Correlações Fortes - Evol vs CK", "Evolutiva vs CK", os.path.join(out_dir, "ck_vs_evol", "histograma_ck_vs_evol_altos.pdf"))

print("Finalizado! Arquivos salvos em '5-Views/resultados/04_correlacoes'")
