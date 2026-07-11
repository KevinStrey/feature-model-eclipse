# Projeto de Análise do Ecossistema de Linhas de Produto de Software (LPS) do Eclipse IDE

Este repositório contém todo o ecossistema, *pipelines* de dados, ferramentas de mineração e scripts analíticos que fundamentam a pesquisa sobre a coevolução e métricas de qualidade de software do ecossistema Eclipse.

O objetivo do projeto é compreender características arquiteturais e históricas extraindo métricas a nível de métodos e classes a partir dos repositórios Git das *features* do Eclipse.

---

## 📊 1. Dicionário de Métricas Coletadas

Neste estudo, o projeto rastreia métricas de duas categorias distintas para permitir correlações ricas de qualidade e evolução: **Evolutivas (Históricas)** e **Estruturais (Baseadas em Código)**.

### 📈 1.1 Métricas Evolutivas (Históricas de Mudança)
Estas métricas são extraídas pela ferramenta `2-JMethodsExtractor`, que minera o histórico do Git, e medem como um método muda (sofre *churn*) ao longo do tempo:

- **BOM (*Birth Of Method*)**: O índice cronológico do *commit* onde o método apareceu pela primeira vez no histórico do projeto (nascimento do método).
- **TACH (*Total Amount Of Change*)**: Quantidade absoluta de linhas que foram adicionadas ou modificadas em um determinado método dentro de um *commit* específico.
- **CHD (*Change Density*)**: Densidade da mudança (TACH dividido pelo tamanho atual em LOC do método durante o *commit*).
- **FCH (*First Change*)**: O índice do primeiro *commit* onde o método sofreu alguma alteração após ter sido criado.
- **LCH (*Last Change*)**: O índice do *commit* em que ocorreu a alteração mais recente e conhecida no método.
- **FRCH (*Frequency of Changes*)**: O número total de vezes (frequência) que o método foi modificado em sua história de vida.
- **WCH (*Weighted Change*)**: Soma do *churn* ponderado temporalmente por uma curva de decaimento (alterações mais recentes recebem peso maior no cálculo da fragilidade do que alterações muito antigas).
- **WCD (*Weighted Change Density*)**: Uma versão ponderada pelo tempo do CHD (Densidade do churn).
- **CSB (*Changes Since Birth*)**: A quantidade absoluta e cumulativa de linhas alteradas desde o momento de criação do método.
- **CSBS (*Changes Since Birth normalized by initial Size*)**: A razão do total de linhas alteradas (CSB) dividido pelo tamanho inicial em LOC que o método possuía no seu momento de "nascimento".
- **ACDF (*Average Change Density per Frequency*)**: Média de densidade de *churn*. Representa a soma total das densidades calculadas dividida pela frequência de modificação (FRCH).
- **LOC (*Lines of Code - Evolutivo*)**: A contagem de linhas de código do método gravadas de forma evolutiva em cada passo do histórico.

### 🏗️ 1.2 Métricas Estruturais (Estáticas CK)
Estas métricas avaliam a complexidade estática do código extraídas pela integração com o `CK` (Chidamber & Kemerer) e operam primariamente nos níveis de classes e métodos:

- **cbo (*Coupling Between Objects*)**: Nível de acoplamento com outras classes. Representa a quantidade de classes que dependem, chamam ou que são chamadas pela estrutura.
- **cboModified**: Versão modificada do CBO padrão.
- **fanin**: Quantidade de classes ou métodos *externos* que dependem ou chamam este artefato atual.
- **fanout**: Quantidade de classes ou métodos *externos* que são invocados ou dependidos pelo artefato atual.
- **wmc (*Weighted Methods per Class*)**: Medida de complexidade ciclomática total (normalmente associada à classe).
- **rfc (*Response For a Class*)**: Tamanho do conjunto de métodos distintos que podem ser engatilhados executando uma mensagem neste objeto (métodos internos + externos chamados).
- **loc**: Tamanho bruto em Linhas de Código (*Lines of Code*) (excluindo comentários e vazias).
- **returnsQty**: Quantidade de instruções `return` no escopo.
- **variablesQty**: Quantidade de variáveis locais declaradas no código.
- **parametersQty**: Número de parâmetros exigidos na assinatura do método.
- **methodsInvokedQty**: Contagem total de quaisquer chamadas de métodos realizadas.
- **methodsInvokedLocalQty**: Invocação direta de métodos que pertencem à própria classe local.
- **methodsInvokedIndirectLocalQty**: Invocação indireta de métodos locais na classe.
- **loopQty**: Quantidade de estruturas de loop e repetição (ex: `for`, `while`, `do-while`).
- **comparisonsQty**: Número de comparações booleanas efetuadas (`==`, `>`, `<`).
- **tryCatchQty**: Contagem de blocos de tratamento de exceções (`try-catch`).
- **parenthesizedExpsQty**: Número de expressões agrupadas/separadas usando parênteses.
- **stringLiteralsQty**: Quantidade de literais em String utilizados (ex: `"texto"`).
- **numbersQty**: Contagem de numerais escalares absolutos instanciados.
- **assignmentsQty**: Quantidade de instruções que efetuam atribuições a variáveis/campos.
- **mathOperationsQty**: Número de operações com operadores matemáticos e lógicos (`+`, `-`, `/`, `*`, `&`).
- **maxNestedBlocksQty**: Profundidade máxima de blocos encadeados (aninhamentos hierárquicos).
- **anonymousClassesQty**: Contagem de uso instanciado de classes anônimas Java internas.
- **innerClassesQty**: Declarações internas de classes dentro de outras (*Inner classes*).
- **lambdasQty**: Contagem de expressões lambdas presentes.
- **uniqueWordsQty**: Riqueza de vocabulário, medindo o número de palavras e variáveis distintas no texto.
- **modifiers**: Presença/uso de modificadores de acesso do Java (`public`, `static`, `final`, etc).
- **logStatementsQty**: Frequência de invocações de logs (usos com classes de logger ou print).
- **hasJavaDoc**: Indicador booleano (0/1) que reflete se existe uma documentação padronizada Javadoc na entidade.

---

## ⚙️ 2. Execução das Ferramentas e Etapas do Pipeline

Para garantir a reprodutibilidade da pesquisa, este projeto foi segmentado numa série de ferramentas acionadas passo-a-passo:

### Passo 1: Repositórios Clonados (`1-Repositorios/`)
- **Descrição:** Contém o repositório bruto base para as minerações com os projetos e ecossistemas sob a umbrella do Eclipse (ex: `egit`, `cdt`, `birt`).
- **O que fazer:** Nada é executado diretamente aqui, pois eles figuram como dados de entrada (input Git) absolutos.

### Passo 2: Extração do Histórico das Métricas Evolutivas (`2-JMethodsExtractor/`)
- **Descrição:** Ferramenta feita nativamente em **Java** estruturada no padrão **Maven**. Trata-se do motor que varre a linha do tempo do Git e extrai a evolução estrutural (TACH, CHD, BOM).
- **Como executar:** 
  Acesse a pasta da aplicação, instale as dependências via Maven, e execute a mineração base:
  ```bash
  cd 2-JMethodsExtractor
  mvn clean install
  ```
  *(O start pode ser feito diretamente pela sua IDE Java usando a classe `FeatureEvolutorTask` ou rodando o target build. O resultado sairá na sub-pasta `/results/`).*

### Passo 3: Mapeamento de Features (`3-Mapeamento_features_simrel/`)
- **Descrição:** Região de apoio que estabelece as regras de correlação temporal das features com as *Releases Simultâneas* (SimRel). Scripts e referências para classificar e particionar arquivos.

### Passo 4: Extração do Histórico das Métricas CK (`4-CKHistoryExtractor/`)
- **Descrição:** Uma segunda ferramenta **Java/Maven** projetada para caminhar também pela história, porém focada nas análises estáticas das classes em cada commit com a ajuda indireta do framework CK.
- **Como executar:** Segue o mesmo padrão do `JMethodsExtractor`, compilando o POM via Maven e extraindo os `.csv` estruturais de evolução arquitetural no formato estático.
  ```bash
  cd 4-CKHistoryExtractor
  mvn clean install
  ```

### Passo 5: Geração das Visualizações e Machine Learning (`5-Views/`)
- **Descrição:** Este passo concentra o Pipeline de **Data Science em Python** para agrupar e correlacionar as métricas colhidas pelas ferramentas Java nas etapas 2 e 4.
- **Como executar o *Pipeline*:**
  Use seu ambiente (venv) com Python, vá até `5-Views` e rode os scripts enumerados localizados na subpasta `scripts/` rigorosamente em sua ordem sequencial. Esses scripts salvarão arquivos na pasta `resultados/`:
  ```bash
  cd 5-Views
  python scripts/01_extracao_metricas_base.py
  python scripts/02_clusterizacao_kmeans.py
  python scripts/03_analise_evolutiva.py
  python scripts/04_geracao_correlacoes.py
  python scripts/05_geracao_graficos_completos.py
  ```
- **Dashboard Interativo (Web UI):** 
  Para examinar gráficos em 3D, resultados interativos e distribuições (ferramenta desenvolvida para o leitor do artigo), você pode usar o pacote Streamlit da seguinte maneira:
  ```bash
  cd dashboard
  streamlit run app.py
  ```

### Passo 6: Análises Sumarizadas (`6-Analises/`)
- **Descrição:** Agrupamento manual com scripts localizados em pastas segregadas para responder a perguntas de pesquisa da redação, como tendências completas por features e resultados de regressões e matrizes de correlações (ex: `BOM_contagem/bom_count_timeline.py`).
