import streamlit as st
import pandas as pd
import os
import glob
import json
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Evolução de Features - Eclipse", page_icon="📊", layout="wide")

st.title("📊 Análise Evolutiva de Features (Arquitetura LPS)")
st.markdown("Este dashboard interativo permite explorar as métricas de evolução das features do Eclipse.")

# Caminhos (hardcoded para o ambiente do usuário)
base_dir = r"c:\Users\Kevin Strey\Desktop\Feature-models"
json_dir = os.path.join(base_dir, r"3-Mapeamento_features_simrel\simrel_mapper\output")
csv_dir = os.path.join(base_dir, r"2-JMethodsExtractor\target\results")
ck_csv_dir = os.path.join(base_dir, r"4-CKHistoryExtractor\target\results")

import re

# --- CARGA DE DADOS COM CACHE ---

@st.cache_data(show_spinner="Carregando timeline (JSONs)...")
def load_timeline():
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    timeline_data = []
    release_dates = {}
    
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            release_name = data.get('release')
            release_date = data.get('date')
            
            if release_date:
                release_dates[release_name] = pd.to_datetime(release_date, utc=True)
            else:
                release_dates[release_name] = pd.Timestamp.min
                
            for feature, feature_data in data.get('mappings', {}).items():
                timeline_data.append({
                    'release': release_name,
                    'feature': feature,
                    'commit': feature_data.get('commit'),
                    'status': feature_data.get('status')
                })
    df_timeline = pd.DataFrame(timeline_data)
    
    # Ordenar cronologicamente pela data real da release
    df_timeline['date'] = df_timeline['release'].map(release_dates)
    df_timeline = df_timeline.sort_values(by='date').drop(columns=['date']).reset_index(drop=True)
    
    return df_timeline

@st.cache_data(show_spinner="Carregando dados da Feature selecionada...")
def load_feature_data(feature_name):
    csv_file = os.path.join(csv_dir, f"{feature_name}_history.csv")
    if not os.path.exists(csv_file):
        return None
    # Lê todos os dados da feature
    return pd.read_csv(csv_file)

@st.cache_data(show_spinner="Carregando métricas CK da DataTools...")
def load_ck_data():
    ck_file = os.path.join(ck_csv_dir, "DataTools_class_history.csv")
    if not os.path.exists(ck_file):
        return None
    try:
        # Tenta ler com separador ';' e ignorando possíveis erros nas linhas mal formatadas
        df_ck = pd.read_csv(ck_file, sep=';', on_bad_lines='skip', low_memory=False)
        
        if not df_ck.empty and 'release' in df_ck.columns:
            numeric_cols = ['cbo', 'wmc', 'rfc', 'lcom', 'dit']
            cols_to_agg = [c for c in numeric_cols if c in df_ck.columns]
            
            # Garantir que as colunas sejam numéricas (podem vir como string por causa do separador de decimal)
            for col in cols_to_agg:
                df_ck[col] = pd.to_numeric(df_ck[col], errors='coerce')
                
            df_ck_agg = df_ck.groupby('release', as_index=False)[cols_to_agg].mean()
            return df_ck_agg
    except Exception as e:
        st.error(f"Erro ao ler CK Data: {e}")
        return None
    return pd.DataFrame()

@st.cache_data(show_spinner="Agregando dados de TODAS as features (pode demorar alguns segundos na 1ª vez)...")
def load_all_aggregated_data():
    all_files = glob.glob(os.path.join(csv_dir, "*_history.csv"))
    agg_list = []
    
    df_timeline = load_timeline()
    release_order = df_timeline['release'].unique().tolist()
    
    # Progresso opcional
    progress_bar = st.progress(0)
    for idx, f in enumerate(all_files):
        feature = os.path.basename(f).replace("_history.csv", "")
        try:
            df = pd.read_csv(f, usecols=['release', 'LOC', 'CSB', 'FRCH', 'methodId'])
            current_state = {}
            known_methods = set()
            feature_metrics = []
            groups = df.groupby('release', sort=False)
            
            for r in release_order:
                births = 0
                deaths = 0
                if r in groups.groups:
                    df_r = groups.get_group(r)
                    last_states = df_r.drop_duplicates('methodId', keep='last')
                    updates = last_states.set_index('methodId')[['LOC', 'CSB', 'FRCH']].to_dict('index')
                    # Contar nascimentos e mortes
                    for m_id, new_vals in updates.items():
                        if m_id not in known_methods:
                            births += 1
                            known_methods.add(m_id)
                        elif m_id in current_state and current_state[m_id]['LOC'] > 0 and new_vals['LOC'] == 0:
                            deaths += 1
                    current_state.update(updates)
                
                active_methods = [v for v in current_state.values() if v['LOC'] > 0]
                total_active = len(active_methods)
                
                if total_active == 0:
                    continue
                    
                total_loc = sum(v['LOC'] for v in active_methods)
                avg_csb = sum(v['CSB'] for v in active_methods) / total_active
                avg_frch = sum(v['FRCH'] for v in active_methods) / total_active
                
                feature_metrics.append({
                    'release': r,
                    'total_loc': total_loc,
                    'avg_loc': total_loc / total_active,
                    'avg_csb': avg_csb,
                    'avg_frch': avg_frch,
                    'total_methods': total_active,
                    'births': births,
                    'deaths': deaths,
                    'feature': feature
                })
            
            if feature_metrics:
                agg_list.append(pd.DataFrame(feature_metrics))
        except Exception as e:
            continue
        progress_bar.progress((idx + 1) / len(all_files))
        
    progress_bar.empty()
    if not agg_list:
        return pd.DataFrame()
    return pd.concat(agg_list, ignore_index=True)


# --- INTERFACE ---
df_timeline = load_timeline()
if os.path.exists(csv_dir):
    available_features = [f.replace("_history.csv", "") for f in os.listdir(csv_dir) if f.endswith("_history.csv")]
else:
    available_features = []
    st.warning("Diretório de resultados não encontrado. Por favor, execute o JMethodsExtractor primeiro.")

st.sidebar.header("Filtros e Configurações")
plot_height = st.sidebar.slider("↕ Altura dos Gráficos (px)", min_value=300, max_value=1200, value=600, step=50)

analysis_type = st.sidebar.radio(
    "Tipo de Análise",
    ["🔍 Específica por Feature", "🌍 Global (Comparação de Features)", "📈 Comparação CK vs Evolutiva (DataTools)"]
)

if analysis_type == "🔍 Específica por Feature":
    st.header("🔍 Análise Específica por Feature")
    selected_feature = st.sidebar.selectbox("Selecione a Feature", sorted(available_features))
    
    df_feature = load_feature_data(selected_feature)
    
    if df_feature is not None:
        st.success(f"Dados carregados: **{len(df_feature):,}** métodos processados na feature **{selected_feature}**.")
        
        # 1. Série Temporal (Line Chart)
        st.subheader("1. Gráfico de Linhas: Evolução Temporal")
        st.markdown("Acompanhe como uma métrica evolui através de todas as versões. Ideal para ver tendências de crescimento ou refatoração.")
        metric_line = st.selectbox("Selecione a métrica:", ['LOC (Soma Total do Tamanho)', 'CSB (Média de Mudanças desde Nascimento)', 'FRCH (Média de Frequência)'])
        
        if metric_line.startswith('LOC'):
            y_col = 'LOC'
        elif metric_line.startswith('CSB'):
            y_col = 'CSB'
        else:
            y_col = 'FRCH'
            
        # Cálculo cumulativo exato do estado do sistema em cada release
        release_order = df_timeline['release'].unique().tolist()
        current_state = {}
        known_methods = set()
        feature_metrics = []
        dense_history = []
        groups = df_feature.groupby('release', sort=False)
        
        for r in release_order:
            births = 0
            deaths = 0
            if r in groups.groups:
                df_r = groups.get_group(r)
                last_states = df_r.drop_duplicates('methodId', keep='last')
                updates = last_states.set_index('methodId')[['LOC', 'CSB', 'FRCH']].to_dict('index')
                # Contar nascimentos e mortes
                for m_id, new_vals in updates.items():
                    if m_id not in known_methods:
                        births += 1
                        known_methods.add(m_id)
                    elif m_id in current_state and current_state[m_id]['LOC'] > 0 and new_vals['LOC'] == 0:
                        deaths += 1
                current_state.update(updates)
            
            active_methods = [v for v in current_state.values() if v['LOC'] > 0]
            total_active = len(active_methods)
            
            if total_active == 0:
                continue
                
            total_loc = sum(v['LOC'] for v in active_methods)
            avg_csb = sum(v['CSB'] for v in active_methods) / total_active
            avg_frch = sum(v['FRCH'] for v in active_methods) / total_active
            
            feature_metrics.append({'release': r, 'LOC': total_loc, 'CSB': avg_csb, 'FRCH': avg_frch, 'total_methods': total_active, 'births': births, 'deaths': deaths})
            
            for m_id, v in current_state.items():
                if v['LOC'] > 0:
                    v_copy = v.copy()
                    v_copy['methodId'] = m_id
                    v_copy['release'] = r
                    dense_history.append(v_copy)
                
        df_agg = pd.DataFrame(feature_metrics)
        df_dense_history = pd.DataFrame(dense_history)
        df_agg['release'] = pd.Categorical(df_agg['release'], categories=release_order, ordered=True)
        df_agg = df_agg.sort_values('release')
        
        fig1 = px.line(df_agg, x='release', y=y_col, markers=True, color_discrete_sequence=['#1f77b4'])
        
        fig1.update_xaxes(type='category', categoryorder='array', categoryarray=release_order)
        
        fig1.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig1, width='stretch')
            
        # 2. Bar Chart: Método Count
        st.subheader("2. Gráfico de Barras: Quantidade de Métodos")
        st.markdown("Veja como a quantidade total de métodos (ativos) evoluiu ao longo das releases da feature.")
        
        fig_bar = px.bar(df_agg, x='release', y='total_methods', color_discrete_sequence=['#2ca02c'])
        fig_bar.update_xaxes(type='category', categoryorder='array', categoryarray=release_order)
        fig_bar.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig_bar, width='stretch')
        
        # 3. Nascimento e Morte de Métodos
        st.subheader("3. Nascimento e Morte de Métodos")
        st.markdown("Quantos métodos **nasceram** (primeira aparição) e **morreram** (LOC → 0) em cada release. Picos de nascimento indicam grandes adições; picos de morte indicam remoções ou refatorações massivas.")
        
        df_life = df_agg[['release', 'births', 'deaths']].melt(id_vars='release', var_name='tipo', value_name='quantidade')
        df_life['tipo'] = df_life['tipo'].map({'births': 'Nascimentos', 'deaths': 'Mortes'})
        
        fig_bom = px.bar(df_life, x='release', y='quantidade', color='tipo', barmode='group',
                         color_discrete_map={'Nascimentos': '#2ca02c', 'Mortes': '#d62728'})
        fig_bom.update_xaxes(type='category', categoryorder='array', categoryarray=release_order)
        fig_bom.update_layout(height=plot_height, yaxis_title='Quantidade de Métodos')
        with st.container(border=True):
            st.plotly_chart(fig_bom, width='stretch')
        
        # 4. Boxplot / Violin
        st.subheader("4. Boxplot / Violino: Distribuição de Métodos")
        st.markdown("Veja como os métodos variam dentro de cada release. Os pontos indicam outliers (métodos 'deus' com extrema complexidade/tamanho).")
        
        col_box1, col_box2 = st.columns(2)
        metric_box = col_box1.selectbox("Métrica para o eixo Y:", ['LOC', 'FRCH', 'CHD', 'CSB'])
        last_n = col_box2.slider("Mostrar as últimas N releases:", 5, len(df_dense_history['release'].unique()), 15)
        
        valid_feature_releases = [r for r in release_order if r in df_dense_history['release'].unique()]
        recent_releases = valid_feature_releases[-last_n:]
        df_box = df_dense_history[df_dense_history['release'].isin(recent_releases)]
        
        fig2 = px.box(df_box, x='release', y=metric_box, points="outliers", color_discrete_sequence=['#ff7f0e'])
        fig2.update_xaxes(type='category', categoryorder='array', categoryarray=recent_releases)
        fig2.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig2, width='stretch')
        
        # 5. Scatter Plot (Bolhas)
        st.subheader("5. Gráfico de Bolhas com Dispersão dos métodos")
        st.markdown("Identifica os métodos críticos. Quadrante superior direito = Alta frequência de mudanças e Alto tamanho.")
        release_order = df_timeline['release'].unique().tolist()
        valid_feature_releases = [r for r in release_order if r in df_dense_history['release'].unique()]
        target_release = st.selectbox("Selecione a Release:", list(reversed(valid_feature_releases)))
        
        df_scatter = df_dense_history[df_dense_history['release'] == target_release].copy()
        
        # Tratamento caso tamanho passe dos limites ou tenha nulos
        df_scatter = df_scatter.fillna(0)
        
        # Ordenar por tamanho (LOC) decrescente para desenhar as bolhas menores por cima das maiores
        df_scatter = df_scatter.sort_values(by='LOC', ascending=False)
        
        fig3 = px.scatter(
            df_scatter, x='FRCH', y='LOC', size='LOC', color='CSB', 
            hover_data=['methodId'], size_max=40, opacity=0.6,
            color_continuous_scale='Turbo'
        )
        
        # Adicionar médias para formar quadrantes
        mean_loc = df_scatter['LOC'].mean()
        mean_frch = df_scatter['FRCH'].mean()
        fig3.add_hline(y=mean_loc, line_dash="dot", line_color="green", annotation_text="Média LOC")
        fig3.add_vline(x=mean_frch, line_dash="dot", line_color="red", annotation_text="Média FRCH")
        
        fig3.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig3, width='stretch')
            
        # 6. Bar Chart: Top Methods by CSB
        st.subheader("6. Ranking de Mudanças: Changes Since Birth (CSB)")
        st.markdown(f"Mostra os 20 métodos com a maior quantidade acumulada de mudanças (refatorações/correções) até a release **{target_release}**.")
        
        df_csb = df_scatter.sort_values(by='CSB', ascending=False).head(20)
        df_csb = df_csb.sort_values(by='CSB', ascending=True)
        
        fig_csb = px.bar(
            df_csb, x='CSB', y='methodId', orientation='h', 
            color='CSB', color_continuous_scale='Reds',
            text='CSB', hover_data=['LOC', 'FRCH']
        )
        
        # Simplifica o eixo Y para mostrar apenas Arquivo::Metodo ao invés do caminho completo
        short_names = [m.split('/')[-1] if '/' in m else m for m in df_csb['methodId']]
        fig_csb.update_yaxes(tickvals=df_csb['methodId'], ticktext=short_names)
        
        fig_csb.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig_csb, width='stretch')
        
    else:
        st.error("Não foi possível carregar os dados desta feature.")

elif analysis_type == "🌍 Global (Comparação de Features)":
    st.header("🌍 Análise Global (Comparação entre Features)")
    st.markdown("Esta visão extrai os dados agregados de **todos** os CSVs para comparar as features lado a lado.")
    
    df_all = load_all_aggregated_data()
    
    if not df_all.empty:
        
        metric_global = st.selectbox("Selecione a Métrica para Comparação:", 
            ['total_loc (Soma de LOC)', 'avg_loc (Média de LOC)', 'avg_csb (Média de Mudanças CSB)', 'avg_frch (Freq. de Mudanças)', 'total_methods (Contagem)'])
        
        y_col = metric_global.split(" ")[0]
        
        # 7. Nascimento e Morte de Métodos Global
        st.subheader("7. Nascimento e Morte de Métodos por Release")
        st.markdown("Quantos métodos nasceram e morreram em cada release do sistema, agregados por feature.")
        
        release_order_global = df_timeline['release'].unique().tolist()
        df_all['release'] = pd.Categorical(df_all['release'], categories=release_order_global, ordered=True)
        df_all = df_all.sort_values('release')
        
        st.markdown("##### 🟢 Nascimentos (empilhados por feature)")
        fig_bom_global = px.bar(df_all, x='release', y='births', color='feature',
                                color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_bom_global.update_xaxes(type='category', categoryorder='array', categoryarray=release_order_global)
        fig_bom_global.update_layout(height=plot_height, yaxis_title='Métodos Nascidos', barmode='stack')
        with st.container(border=True):
            st.plotly_chart(fig_bom_global, width='stretch')
        
        st.markdown("##### 🔴 Mortes (empilhadas por feature)")
        fig_death_global = px.bar(df_all, x='release', y='deaths', color='feature',
                                  color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_death_global.update_xaxes(type='category', categoryorder='array', categoryarray=release_order_global)
        fig_death_global.update_layout(height=plot_height, yaxis_title='Métodos Mortos', barmode='stack')
        with st.container(border=True):
            st.plotly_chart(fig_death_global, width='stretch')
        
        # 8. Evolução Conjunta (Line Chart)
        st.subheader("8. Evolução Conjunta (Gráfico de Linhas)")
        st.markdown("Veja quais repositórios cresceram ou mudaram juntos ao longo do tempo (linhas com o mesmo padrão).")
        
        # (release já categorizado acima)
        
        fig5 = px.line(df_all, x='release', y=y_col, color='feature', markers=True)
        fig5.update_xaxes(type='category', categoryorder='array', categoryarray=release_order_global)
        fig5.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig5, width='stretch')
            
        # 9. Ranking Atual (Bar Chart)
        st.subheader("9. Ranking por Repositório (Última Release)")
        st.markdown("Descubra rapidamente qual é o maior repositório ou qual sofreu mais mudanças até o estado atual da feature.")
        
        # Pega a última release disponível para cada feature
        latest_data = df_all.sort_values('release').groupby('feature').tail(1)
        latest_data = latest_data.sort_values(y_col, ascending=False)
        
        fig6 = px.bar(latest_data, x=y_col, y='feature', orientation='h', color=y_col, color_continuous_scale='Blues')
        fig6.update_layout(height=plot_height, yaxis={'categoryorder':'total ascending'})
        with st.container(border=True):
            st.plotly_chart(fig6, width='stretch')
        
    else:
        st.warning("Nenhum dado agregado encontrado.")

elif analysis_type == "📈 Comparação CK vs Evolutiva (DataTools)":
    st.header("📈 Comparação CK vs Evolutiva (DataTools)")
    st.markdown("Esta visão correlaciona as médias das métricas de design Orientado a Objetos (CK) com as métricas evolutivas da feature DataTools.")
    
    df_ck_agg = load_ck_data()
    df_feature = load_feature_data("DataTools")
    
    if df_ck_agg is None or df_ck_agg.empty:
        st.error("Não foi possível carregar os dados CK da DataTools. Certifique-se de que o arquivo `DataTools_class_history.csv` existe.")
    elif df_feature is None or df_feature.empty:
        st.error("Não foi possível carregar os dados evolutivos da DataTools.")
    else:
        # 1. Agregação Evolutiva da DataTools
        release_order = df_timeline['release'].unique().tolist()
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
                    'release': r,
                    'LOC_Evol': total_loc,
                    'CSB_Evol': avg_csb,
                    'FRCH_Evol': avg_frch,
                })
        
        df_evol_agg = pd.DataFrame(feature_metrics)
        
        # Merge CK com Evolutiva
        df_merged = pd.merge(df_evol_agg, df_ck_agg, on='release', how='inner')
        
        # Garantir a ordem temporal correta
        df_merged['release'] = pd.Categorical(df_merged['release'], categories=release_order, ordered=True)
        df_merged = df_merged.sort_values('release')
        
        if not df_merged.empty:
            st.success("Dados cruzados com sucesso!")
            
            # Gráfico 1: Evolução Temporal com 2 eixos
            st.subheader("1. Evolução Comparada (Eixo Duplo)")
            col1, col2 = st.columns(2)
            metrica_ck = col1.selectbox("Selecione a Métrica CK (Média por Classe):", ['wmc', 'cbo', 'rfc', 'lcom', 'dit'])
            metrica_evol = col2.selectbox("Selecione a Métrica Evolutiva:", ['CSB_Evol', 'FRCH_Evol', 'LOC_Evol'])
            
            fig_dual = go.Figure()
            
            fig_dual.add_trace(go.Scatter(
                x=df_merged['release'], y=df_merged[metrica_ck],
                name=f"{metrica_ck.upper()} (CK)",
                line=dict(color="#1f77b4", width=3)
            ))
            
            fig_dual.add_trace(go.Scatter(
                x=df_merged['release'], y=df_merged[metrica_evol],
                name=f"{metrica_evol.replace('_Evol', '')} (Evolutivo)",
                yaxis="y2",
                line=dict(color="#d62728", width=3, dash='dot')
            ))
            
            fig_dual.update_layout(
                title=f"Evolução: {metrica_ck.upper()} vs {metrica_evol.replace('_Evol', '')}",
                xaxis=dict(title="Release"),
                yaxis=dict(title=metrica_ck.upper(), title_font=dict(color="#1f77b4"), tickfont=dict(color="#1f77b4")),
                yaxis2=dict(title=metrica_evol.replace('_Evol', ''), title_font=dict(color="#d62728"), tickfont=dict(color="#d62728"), overlaying="y", side="right"),
                height=plot_height
            )
            
            with st.container(border=True):
                st.plotly_chart(fig_dual, width='stretch')
                
            # Gráfico 2: Matriz de Correlação
            st.subheader("2. Matriz de Correlação (Pearson)")
            st.markdown("Verifica a correlação linear entre as métricas. Valores próximos de 1 indicam forte correlação positiva (quando uma sobe, a outra sobe).")
            
            cols_corr = ['wmc', 'cbo', 'rfc', 'lcom', 'dit', 'CSB_Evol', 'FRCH_Evol', 'LOC_Evol']
            # Filtra apenas colunas presentes
            cols_corr = [c for c in cols_corr if c in df_merged.columns]
            
            df_corr = df_merged[cols_corr].corr()
            
            # Renomeia para ficar mais amigável
            friendly_names = {c: c.replace('_Evol', '').upper() for c in cols_corr}
            df_corr = df_corr.rename(columns=friendly_names, index=friendly_names)
            
            fig_corr = px.imshow(
                df_corr, 
                text_auto=".2f", 
                color_continuous_scale='RdBu_r', 
                zmin=-1, zmax=1,
                aspect="auto"
            )
            fig_corr.update_layout(height=plot_height)
            
            with st.container(border=True):
                st.plotly_chart(fig_corr, width='stretch')
                
            # Gráfico 3: Scatter
            st.subheader("3. Dispersão (Correlação Direta)")
            col3, col4 = st.columns(2)
            scatter_x = col3.selectbox("Eixo X (CK):", ['cbo', 'wmc', 'rfc', 'lcom', 'dit'])
            scatter_y = col4.selectbox("Eixo Y (Evolutivo):", ['CSB_Evol', 'FRCH_Evol', 'LOC_Evol'])
            
            fig_scatter = px.scatter(
                df_merged, x=scatter_x, y=scatter_y, 
                hover_data=['release'],
                title=f"{scatter_x.upper()} vs {scatter_y.replace('_Evol', '')}",
                color='release'
            )
            fig_scatter.update_layout(height=plot_height)
            
            with st.container(border=True):
                st.plotly_chart(fig_scatter, width='stretch')
                
        else:
            st.warning("Não foi possível cruzar os dados CK e Evolutivos. Verifique se as releases coincidem.")
