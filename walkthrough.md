# Simrel Mapper — Implementação Concluída

O pipeline de mapeamento de features do Eclipse Simrel foi implementado com sucesso. Ele foi projetado para ser **determinístico, auditável e rodar 100% offline** (sem chamadas de rede), garantindo a reprodutibilidade necessária para pesquisas científicas de LPS.

## Arquitetura Implementada

A implementação seguiu a separação de responsabilidades proposta:

1. **Ingestion (Parser e Reader)**
   - `simrel_reader.py`: Navega pelo repositório `simrel.build` usando a API pura do `gitpython`, iterando sobre tags (releases) e lendo blobs diretamente das árvores, garantindo velocidade sem necessidade de checkout ou alteração do estado local do repositório.
   - `aggrcon_parser.py`: Processador inteligente de XML que detecta automaticamente entre o formato antigo (`.b3aggrcon`, namespace `b3`) e novo (`.aggrcon`, namespace `cbi`). As regras para A1 (versionRange), A2 (URL SemVer) e A3 (URL + buildId) foram validadas com fixtures reais das releases analisadas (Juno e 2026). O caso especial de *ranges* de dependências (ex: `[1.0.0,2.0.0)`) em versões recentes foi implementado corretamente para que somente versões exatas acionem A1.

2. **Heurísticas (Votação e Resolução)**
   - O `VotingEngine` orquestra a cadeia de resolução:
   - **H1 (Tag Match)**: Inclui suporte a todas as 5 subvariantes (`H1-exact`, `H1-date-suffix`, `H1-date-prefix`, `H1-loose`, `H1-partial`), extraindo magicamente os blocos numéricos das tags dos projetos de features (ex: transformando `CDT_10_3_1` em `[10, 3, 1]`) e validando correspondências complexas de substring.
   - **H4 (Maintenance Branch)**: Identifica branches padrão (`stable-X.Y`, `R1_5_maintenance`, etc.) e busca o commit limite que antecede imediatamente o `timestamp` injetado na feature do Simrel.
   - **H0 (Timestamp Global Fallback)**: Executa busca `--all` pela árvore inteira de commits limitando-se pelo tempo se as heurísticas mais precisas não fornecerem solução.

3. **Auditoria Estruturada**
   - Utilizamos a biblioteca `structlog` no `audit/logger.py` para gerar logs contextualizados (`release`, `feature`, `commit`, `weight`). Qualquer decisão tomada por empates, e todos os votos lançados, são explicitados detalhadamente na tela. 

## Validação e Testes

Foi construída uma suíte de testes com a biblioteca `pytest` focada nas lógicas críticas. 
A suíte foi executada e **100% dos 8 testes de regressão, parseamento e heurística passaram**.

```powershell
python -m pytest tests/ -v
```

> [!TIP]
> Os testes `test_heuristics.py` interagem com os clones locais reais (`CDT` e `EGIT`), verificando a eficácia real das abordagens H1, H0 e H4. As lógicas de parser também recebem dados binários reais de blobs `.b3aggrcon`/`.aggrcon` capturados de repositórios reais durante o ambiente de dev (`fixtures/`).

### Teste de Execução Completa (JunoSR0)

O comando principal orquestrador já está operacional:

```powershell
$env:PYTHONPATH="C:\Users\Kevin Strey\Desktop\Feature-models\3-Mapeamento_features_simrel"
python simrel_mapper/main.py run --release JunoSR0
```

Este comando já escaneou os repositórios reais. Mapeamos com sucesso features difíceis como PTP e GMF Runtime com heurísticas complexas de fallback e empates intencionalmente reportados (`NEEDS REVIEW` para 6 candidatos no PTP, por exemplo). Features que não estão cadastradas no `REPOSITORIES` da root configuration foram ignoradas adequadamente. Os resultados completos do Mapeamento são salvos em `simrel_mapper/output/JunoSR0.json`.

## Próximos Passos e Comandos CLI

Você pode executar agora qualquer subcomando em larga escala:

- Para ler **todas as 61 releases** do `simrel.build`:
  `python simrel_mapper/main.py run --all`

- Para compilar a estatística de cobertura de **taxa de sucesso** das heurísticas e exibi-las em uma tabela Rica:
  `python simrel_mapper/main.py stats`

- Para auditar visualmente no terminal os itens com status `NEEDS REVIEW`:
  `python simrel_mapper/main.py review`
