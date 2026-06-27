import pandas as pd
import os
import glob
import json
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'serif'

base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, r"3-Mapeamento_features_simrel\simrel_mapper\output")
csv_dir = os.path.join(base_dir, r"2-JMethodsExtractor\target\results")
ck_csv_dir = os.path.join(base_dir, r"4-CKHistoryExtractor\target\results")

out_dir = os.path.join(base_dir, r"5-Views\resultados\03_analise_evolutiva")
os.makedirs(os.path.join(out_dir, "metricas_detalhadas", "features_especificas"), exist_ok=True)
os.makedirs(os.path.join(out_dir, "metricas_detalhadas", "global"), exist_ok=True)
os.makedirs(os.path.join(out_dir, "ck_vs_evolutivo", "features_especificas"), exist_ok=True)
os.makedirs(os.path.join(out_dir, "ck_vs_evolutivo", "global"), exist_ok=True)
print("Pastas preparadas com sucesso!")

ck_metrics_list = [
    "cbo","cboModified","fanin","fanout","wmc","rfc","loc","returnsQty",
    "variablesQty","parametersQty","methodsInvokedQty","methodsInvokedLocalQty",
    "methodsInvokedIndirectLocalQty","loopQty","comparisonsQty","tryCatchQty",
    "parenthesizedExpsQty","stringLiteralsQty","numbersQty","assignmentsQty",
    "mathOperationsQty","maxNestedBlocksQty","anonymousClassesQty","innerClassesQty",
    "lambdasQty","uniqueWordsQty","modifiers","logStatementsQty","hasJavaDoc"
]

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
    ck_file = os.path.join(ck_csv_dir, f"{feature_name}_class_history.csv")
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
print(f"Features disponíveis (Evolutivo): {len(available_features)}")

def process_evolution(df_feature, release_order):
    current_state = {}
    known_methods = set()
    feature_metrics = []
    groups = df_feature.groupby('release', sort=False)
    for r in release_order:
        births = deaths = 0
        if r in groups.groups:
            df_r = groups.get_group(r)
            last_states = df_r.drop_duplicates('methodId', keep='last')
            updates = last_states.set_index('methodId')[['LOC', 'CSB', 'FRCH']].to_dict('index')
            for m_id, new_vals in updates.items():
                if m_id not in known_methods:
                    births += 1
                    known_methods.add(m_id)
                elif m_id in current_state and current_state[m_id]['LOC'] > 0 and new_vals['LOC'] == 0:
                    deaths += 1
            current_state.update(updates)
        active_methods = [v for v in current_state.values() if v['LOC'] > 0]
        total_active = len(active_methods)
        if total_active > 0:
            total_loc = sum(v['LOC'] for v in active_methods)
            avg_csb = sum(v['CSB'] for v in active_methods) / total_active
            avg_frch = sum(v['FRCH'] for v in active_methods) / total_active
            feature_metrics.append({
                'release': r, 'LOC': total_loc, 'CSB': avg_csb, 'FRCH': avg_frch,
                'total_methods': total_active, 'births': births, 'deaths': deaths
            })
    df_agg = pd.DataFrame(feature_metrics)
    if not df_agg.empty:
        df_agg['release'] = pd.Categorical(df_agg['release'], categories=release_order, ordered=True)
        df_agg = df_agg.sort_values('release')
    return df_agg

release_order = df_timeline['release'].unique().tolist()
dict_evol_agg = {}

print("Processando dados evolutivos por feature...")
for feat in available_features:
    df_f = load_feature_data(feat)
    if df_f is not None and not df_f.empty:
        df_agg = process_evolution(df_f, release_order)
        if not df_agg.empty:
            dict_evol_agg[feat] = df_agg

print("Processando dados evolutivos Globais (Sistema todo)...")
if dict_evol_agg:
    all_evol = pd.concat(dict_evol_agg.values())
    global_evol_agg = all_evol.groupby('release', observed=False).agg({
        'LOC': 'sum', 'total_methods': 'sum', 'births': 'sum', 'deaths': 'sum',
        'CSB': 'mean', 'FRCH': 'mean'
    }).reset_index()
else:
    global_evol_agg = pd.DataFrame()
print("Concluído!")

def plot_evol_trends(df, title, save_path):
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    sns.lineplot(data=df, x='release', y='LOC', ax=axes[0], marker="o", color="blue")
    axes[0].set_title(f"{title} - Tamanho (LOC)")
    axes[0].set_ylabel("Linhas de Código")
    
    sns.lineplot(data=df, x='release', y='CSB', ax=axes[1], marker="s", color="orange")
    axes[1].set_title(f"{title} - Mudanças por Método (CSB Médio)")
    axes[1].set_ylabel("Mudanças (CSB)")
    
    sns.lineplot(data=df, x='release', y='FRCH', ax=axes[2], marker="D", color="green")
    axes[2].set_title(f"{title} - Frequência de Mudança (FRCH Médio)")
    axes[2].set_ylabel("Freq. Mudança")
    axes[2].set_xlabel("Release")
    
    for ax in axes:
        ax.tick_params(axis='x', rotation=90)
            
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

print("Gerando gráficos Evolutivos por Feature...")
for feat, df_agg in dict_evol_agg.items():
    save_path = os.path.join(out_dir, "metricas_detalhadas", "features_especificas", f"{feat}.pdf")
    plot_evol_trends(df_agg, f"Evolução - {feat}", save_path)

if not global_evol_agg.empty:
    print("Gerando gráfico Evolutivo Global...")
    save_path = os.path.join(out_dir, "metricas_detalhadas", "global", "sistema_completo_evolutivo.pdf")
    plot_evol_trends(global_evol_agg, "Evolução - Sistema Global", save_path)


dict_ck_agg = {}
print("Procurando dados CK e realizando agregação...")
for feat in available_features:
    df_ck = load_ck_data(feat)
    if df_ck is not None and not df_ck.empty:
        dict_ck_agg[feat] = df_ck
        print(f" -> Encontrado CK para: {feat}")
    else:
        print(f" -> Nenhum dado CK carregado para: {feat}")

dict_merged = {}
for feat, df_evol in dict_evol_agg.items():
    if feat in dict_ck_agg:
        df_ck = dict_ck_agg[feat]
        merged = pd.merge(df_evol, df_ck, on='release', how='inner')
        if not merged.empty:
            dict_merged[feat] = merged
        else:
            print(f"Aviso: Merge vazio para {feat}. Verifique se as releases coincidem.")

global_merged = None
if dict_ck_agg and not global_evol_agg.empty:
    all_ck = pd.concat(dict_ck_agg.values())
    global_ck_agg = all_ck.groupby('release', observed=False).mean(numeric_only=True).reset_index()
    global_merged = pd.merge(global_evol_agg, global_ck_agg, on='release', how='inner')

def plot_ck_vs_evolutivo(df, feat_name, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    
    for metric in ck_metrics_list:
        if metric not in df.columns:
            continue
            
        fig, ax1 = plt.subplots(figsize=(16, 5))
        ax2 = ax1.twinx()
        
        sns.lineplot(data=df, x='release', y=metric, ax=ax1, marker="o", color="blue", label=f"{metric.upper()} (Média CK)")
        sns.lineplot(data=df, x='release', y='CSB', ax=ax2, marker="s", color="red", linestyle="--", label="CSB (Média Evolutivo)")
        
        ax1.set_xlabel("Release")
        ax1.set_ylabel(metric.upper(), color="blue")
        ax2.set_ylabel("CSB", color="red")
        
        ax1.tick_params(axis='x', rotation=90)
        plt.title(f"{feat_name}: {metric.upper()} vs CSB")
        
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        if ax2.get_legend() is not None: ax2.get_legend().remove()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='lower right', bbox_to_anchor=(1, 1.05), ncol=2)
        
        fig.tight_layout()
        plt.savefig(os.path.join(save_dir, f"{metric}_vs_CSB.pdf"), bbox_inches='tight')
        plt.close()

    cols = ck_metrics_list + ['CSB', 'FRCH', 'LOC']
    cols_exist = [c for c in cols if c in df.columns]
    if len(cols_exist) > 1:
        corr = df[cols_exist].corr(numeric_only=True)
        plt.figure(figsize=(24, 20))
        sns.heatmap(corr, annot=True, cmap="RdBu_r", vmin=-1, vmax=1, fmt=".2f", annot_kws={"size": 8})
        plt.title(f"{feat_name}: Correlação CK vs Evolutivo")
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, "correlacao.pdf"))
        plt.close()

print("Gerando gráficos CK vs Evolutivo por Feature...")
for feat, df_m in dict_merged.items():
    feat_dir = os.path.join(out_dir, "ck_vs_evolutivo", "features_especificas", feat)
    plot_ck_vs_evolutivo(df_m, feat, feat_dir)

print("Gerando gráficos CK vs Evolutivo Global...")
if global_merged is not None and not global_merged.empty:
    global_dir = os.path.join(out_dir, "ck_vs_evolutivo", "global", "sistema_completo")
    plot_ck_vs_evolutivo(global_merged, "Sistema Global", global_dir)
    
print("Todos os processos concluídos com sucesso! Arquivos na pasta resultados/03_analise_evolutiva/")


