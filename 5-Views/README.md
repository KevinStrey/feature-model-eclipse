# 5-Views: Extração, Análise e Visualização de Métricas LPS

Bem-vindo ao estágio final (Pipeline Analítico) do nosso projeto de análise do ecossistema de Linhas de Produto de Software (LPS) do Eclipse IDE. 

A finalidade desta pasta é processar os dados históricos brutos (extraídos nos estágios anteriores) e gerar visualizações, correlações e agrupamentos evolutivos capazes de provar as hipóteses do nosso artigo.

Para facilitar a reproducibilidade e avaliação da metodologia, estruturamos os códigos e resultados numéricos em um pipeline sequencial claro.

## 📂 Estrutura de Diretórios

- **`/scripts`**: Contém todos os códigos-fonte da nossa ferramenta, prefixados na sua exata ordem de execução (01 a 05).
- **`/resultados`**: Todo script em `/scripts` que gera PDFs ou CSVs injetará os outputs em sua respectiva subpasta neste diretório.
- **`/dashboard`**: Uma aplicação em Python/Streamlit (`app.py`) usada para análise de sensibilidade e verificação visual dinâmica.

## 🚀 O Pipeline de Processamento (Scripts)

Nossa ferramenta segue um *pipeline* rígido de 5 passos para inferir os dados distribuídos.

1. **`01_extracao_metricas_base.py`**
   - **Objetivo**: Inicializa o agrupamento das *features*. Calcula Deltas (LCH, LOC) e métricas acumulativas de todos os métodos ativos desde o nascimento da feature.
   - **Saída**: `/resultados/01_extracao_base`
2. **`02_clusterizacao_kmeans.py`**
   - **Objetivo**: Aplica Machine Learning (K-Means com K=3) com base nos resultados estáticos e dinâmicos para agrupar as *features* em perfis evolutivos arquiteturais através dos eixos: Tamanho, Complexidade e Mudança (CSB).
   - **Saída**: `/resultados/02_clusterizacao` (Contendo matrizes e Gráficos de Radar das features).
3. **`03_analise_evolutiva.py`**
   - **Objetivo**: Gera visualizações de séries temporais ao longo das *Releases*. Aplica escalas lineares e logarítmicas/normalizadas para atenuar as distorções entre features monolíticas e anêmicas.
   - **Saída**: `/resultados/03_analise_evolutiva/timeline_loc`
4. **`04_geracao_correlacoes.py`**
   - **Objetivo**: Encontra correlações de Spearman (p < 0.05) entre as métricas de coevolução estática (CK) e histórica, identificando gargalos na evolução do repositório.
   - **Saída**: `/resultados/04_correlacoes`
5. **`05_geracao_graficos_completos.py`**
   - **Objetivo**: Realiza um cruzamento profundo e gera plotagens detalhadas entre métricas CK e métricas evolutivas individuais.
   - **Saída**: `/resultados/03_analise_evolutiva/metricas_detalhadas` e `/resultados/03_analise_evolutiva/ck_vs_evolutivo` (Dependendo das flags de agregação).

## 📊 Reproduzindo a UI Interativa

Caso deseje usar a interface Streamlit desenvolvida para a avaliação empírica do artigo:

```bash
cd dashboard
streamlit run app.py
```
