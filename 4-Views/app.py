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

import re

# --- CARGA DE DADOS COM CACHE ---

def get_release_sort_key(release_name):
    """
    Retorna uma tupla (ano, nome) para ordenar as releases do Eclipse cronologicamente.
    Juno(2012), Kepler(2013), Luna(2014), Mars(2015), Neon(2016), Oxygen(2017), Photon(2018).
    """
    name_upper = release_name.upper()
    year = 9999
    if "JUNO" in name_upper: year = 2012
    elif "KEPLER" in name_upper: year = 2013
    elif "LUNA" in name_upper: year = 2014
    elif "MARS" in name_upper: year = 2015
    elif "NEON" in name_upper: year = 2016
    elif "OXYGEN" in name_upper: year = 2017
    elif "PHOTON" in name_upper: year = 2018
    else:
        # Extrai ano de releases no formato 2018-09, S2015..., z2014...
        m = re.search(r'(20\d{2})', release_name)
        if m:
            year = int(m.group(1))
    return (year, release_name)

@st.cache_data(show_spinner="Carregando timeline (JSONs)...")
def load_timeline():
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    timeline_data = []
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            release_name = data.get('release')
            for feature, feature_data in data.get('mappings', {}).items():
                timeline_data.append({
                    'release': release_name,
                    'feature': feature,
                    'commit': feature_data.get('commit'),
                    'status': feature_data.get('status')
                })
    df_timeline = pd.DataFrame(timeline_data)
    
    # Ordenar cronologicamente
    df_timeline['sort_key'] = df_timeline['release'].apply(get_release_sort_key)
    df_timeline = df_timeline.sort_values(by='sort_key').drop(columns=['sort_key']).reset_index(drop=True)
    
    return df_timeline

@st.cache_data(show_spinner="Carregando dados da Feature selecionada...")
def load_feature_data(feature_name):
    csv_file = os.path.join(csv_dir, f"{feature_name}_history.csv")
    if not os.path.exists(csv_file):
        return None
    # Lê todos os dados da feature
    return pd.read_csv(csv_file)

@st.cache_data(show_spinner="Agregando dados de TODAS as features (pode demorar alguns segundos na 1ª vez)...")
def load_all_aggregated_data():
    all_files = glob.glob(os.path.join(csv_dir, "*_history.csv"))
    agg_list = []
    
    # Progresso opcional
    progress_bar = st.progress(0)
    for idx, f in enumerate(all_files):
        feature = os.path.basename(f).replace("_history.csv", "")
        try:
            # Lemos apenas as colunas necessárias para não estourar a memória (RAM)
            df = pd.read_csv(f, usecols=['release', 'LOC', 'TACH', 'FRCH', 'methodId'])
            agg = df.groupby('release').agg(
                total_loc=('LOC', 'sum'),
                avg_loc=('LOC', 'mean'),
                avg_tach=('TACH', 'mean'),
                avg_frch=('FRCH', 'mean'),
                total_methods=('methodId', 'count')
            ).reset_index()
            agg['feature'] = feature
            agg_list.append(agg)
        except Exception as e:
            continue
        progress_bar.progress((idx + 1) / len(all_files))
        
    progress_bar.empty()
    if not agg_list:
        return pd.DataFrame()
    return pd.concat(agg_list, ignore_index=True)


# --- INTERFACE ---
df_timeline = load_timeline()
available_features = [f.replace("_history.csv", "") for f in os.listdir(csv_dir) if f.endswith("_history.csv")]

st.sidebar.header("Filtros e Configurações")
plot_height = st.sidebar.slider("↕ Altura dos Gráficos (px)", min_value=300, max_value=1200, value=600, step=50)

analysis_type = st.sidebar.radio(
    "Tipo de Análise",
    ["🔍 Específica por Feature", "🌍 Global (Comparação de Features)"]
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
        metric_line = st.selectbox("Selecione a métrica:", ['LOC (Soma Total do Tamanho)', 'TACH (Média de Mudanças)', 'FRCH (Média de Frequência)'])
        
        if metric_line.startswith('LOC'):
            df_agg = df_feature.groupby('release')['LOC'].sum().reset_index()
            y_col = 'LOC'
        elif metric_line.startswith('TACH'):
            df_agg = df_feature.groupby('release')['TACH'].mean().reset_index()
            y_col = 'TACH'
        else:
            df_agg = df_feature.groupby('release')['FRCH'].mean().reset_index()
            y_col = 'FRCH'
            
        fig1 = px.line(df_agg, x='release', y=y_col, markers=True, color_discrete_sequence=['#1f77b4'])
        fig1.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig1, use_container_width=True)
        
        # 2. Boxplot / Violin
        st.subheader("2. Boxplot / Violino: Distribuição de Métodos")
        st.markdown("Veja como os métodos variam dentro de cada release. Os pontos indicam outliers (métodos 'deus' com extrema complexidade/tamanho).")
        
        col_box1, col_box2 = st.columns(2)
        metric_box = col_box1.selectbox("Métrica para o eixo Y:", ['LOC', 'TACH', 'FRCH', 'CHD', 'CSB'])
        last_n = col_box2.slider("Mostrar as últimas N releases:", 5, len(df_feature['release'].unique()), 15)
        
        recent_releases = sorted(df_feature['release'].unique())[-last_n:]
        df_box = df_feature[df_feature['release'].isin(recent_releases)]
        
        fig2 = px.box(df_box, x='release', y=metric_box, points="outliers", color_discrete_sequence=['#ff7f0e'])
        fig2.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig2, use_container_width=True)
        
        # 3. Scatter Plot (Bolhas)
        st.subheader("3. Gráfico de Dispersão com Bolhas: Matriz de Risco")
        st.markdown("Identifica os métodos críticos. Quadrante superior direito = Alta frequência de mudanças e Alto tamanho.")
        release_order = df_timeline['release'].unique().tolist()
        valid_feature_releases = [r for r in release_order if r in df_feature['release'].unique()]
        target_release = st.selectbox("Selecione a Release:", list(reversed(valid_feature_releases)))
        
        target_idx = release_order.index(target_release)
        allowed_releases = release_order[:target_idx+1]
        
        df_history = df_feature[df_feature['release'].isin(allowed_releases)]
        df_scatter = df_history.drop_duplicates(subset=['methodId'], keep='last')
        
        # Tratamento caso tamanho passe dos limites ou tenha nulos
        df_scatter = df_scatter.fillna(0)
        
        fig3 = px.scatter(
            df_scatter, x='FRCH', y='LOC', size='LOC', color='TACH', 
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
            st.plotly_chart(fig3, use_container_width=True)
            
        # 4. Bar Chart: Top Methods by CSB
        st.subheader("4. Ranking de Mudanças: Changes Since Birth (CSB)")
        st.markdown(f"Mostra os 20 métodos com a maior quantidade acumulada de mudanças (refatorações/correções) até a release **{target_release}**.")
        
        df_csb = df_scatter.sort_values(by='CSB', ascending=False).head(20)
        df_csb = df_csb.sort_values(by='CSB', ascending=True)
        
        fig_csb = px.bar(
            df_csb, x='CSB', y='methodId', orientation='h', 
            color='CSB', color_continuous_scale='Reds',
            text='CSB', hover_data=['LOC', 'TACH', 'FRCH']
        )
        
        # Simplifica o eixo Y para mostrar apenas Arquivo::Metodo ao invés do caminho completo
        short_names = [m.split('/')[-1] if '/' in m else m for m in df_csb['methodId']]
        fig_csb.update_yaxes(tickvals=df_csb['methodId'], ticktext=short_names)
        
        fig_csb.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig_csb, use_container_width=True)
        
    else:
        st.error("Não foi possível carregar os dados desta feature.")

else: # Análise Global
    st.header("🌍 Análise Global (Comparação entre Features)")
    st.markdown("Esta visão extrai os dados agregados de **todos** os CSVs para comparar as features lado a lado.")
    
    df_all = load_all_aggregated_data()
    
    if not df_all.empty:
        # 5. Heatmap
        st.subheader("5. Mapa de Calor (Heatmap) de Evolução")
        st.markdown("Ideal para encontrar 'hotspots' (em vermelho) onde uma feature teve um pico extremo de complexidade ou manutenção em determinada release.")
        metric_heat = st.selectbox("Métrica para o Mapa de Calor:", 
                                   ['total_loc (Soma de LOC)', 'avg_loc (Média de LOC)', 'avg_tach (Média de Mudanças)', 'avg_frch (Freq. de Mudanças)'])
        
        metric_col = metric_heat.split(" ")[0]
        df_pivot = df_all.pivot(index='feature', columns='release', values=metric_col).fillna(0)
        
        fig4 = px.imshow(
            df_pivot, 
            aspect="auto", 
            color_continuous_scale='Reds',
            labels=dict(x="Release", y="Feature", color=metric_col)
        )
        fig4.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig4, use_container_width=True)
        
        # 6. Stacked Area
        st.subheader("6. Gráfico de Área Empilhada (Stacked Area)")
        st.markdown("Mostra o quanto cada feature contribui para o tamanho total do sistema ao longo do tempo.")
        
        # Filtrar top features para o gráfico não ficar ilegível
        top_features = df_all.groupby('feature')['total_loc'].max().nlargest(10).index
        df_stacked = df_all[df_all['feature'].isin(top_features)]
        
        # 1. Preencher buracos (Sparse para Dense) para o gráfico de área não bugar
        df_pivot_area = df_stacked.pivot(index='release', columns='feature', values='total_loc').fillna(0)
        df_dense = df_pivot_area.reset_index().melt(id_vars='release', value_name='total_loc')
        
        # 2. Obter a ordem cronológica correta a partir da timeline
        release_order = df_timeline['release'].unique().tolist()
        
        fig5 = px.area(
            df_dense, x='release', y='total_loc', color='feature',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        # 3. Forçar o Plotly a não tentar converter "2018-09" em data e usar nossa ordem
        fig5.update_xaxes(type='category', categoryorder='array', categoryarray=release_order)
        
        fig5.update_layout(height=plot_height)
        with st.container(border=True):
            st.plotly_chart(fig5, use_container_width=True)
        
    else:
        st.warning("Nenhum dado agregado encontrado.")
