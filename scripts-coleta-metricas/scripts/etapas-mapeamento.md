# 🎯 Conclusão do Mapeamento Massivo do SimRel

Concluímos com sucesso a coleta e mapeamento profundo das versões dos componentes do Eclipse SimRel, extraindo metadados de Git Commits para **61 releases históricas** englobando **17 repositórios completos** (de `birt` a `windowbuilder`).

## O que foi desenvolvido

Nossa estratégia baseada apenas nos nomes de `Tags` (Fuzzy Tagging) era suscetível a erros, principalmente analisando versões antigas do Eclipse onde a nomenclatura mudava com muita frequência. Para processar o histórico massivo de 20 anos, implementamos três estratégias vitais:

1. **Heurística de Time-Travel (A Bala de Prata):**
   *A maioria absoluta* dos pacotes do Eclipse contém um *timestamp* atrelado à versão (Ex: CDT `9.5.3.201809121146`). Criamos uma heurística que extrai cirurgicamente esse horário (`12 de Setembro de 2018 às 11:46:00`) e instrui o Git a encontrar o último commit que antecede este exato segundo no tempo.
   - Isso desbancou a necessidade de adivinhar nomes de tags.
   - Proveu eficiência absurda na busca de M3, M7, RC1, RC4, que dificilmente possuíam suas próprias tags no repositório.

2. **Heurística de Fallback Pickaxe (Manifest.mf):**
   Para ferramentas mais arcaicas ou empacotadas sem *timestamp* (Ex: `DATATOOLS 1.14.100`), ativamos uma varredura que cruza a árvore do Git (`git log -S`) buscando exatamente pelo momento onde a string `Bundle-Version: <versão>` foi introduzida no manifesto do projeto. 

3. **Timeouts de Proteção:**
   Projetos titânicos como `ECLIPSELINK` rodando buscas reversas completas (`--all`) geravam lentidões infinitas no Git do Windows. Para corrigir isso no meio da execução, acoplamos um controle seguro de *Timeout* que evita o congelamento do processo.

## Resultados

Na pasta [releases/mappings](file:///c:/Users/Kevin%20Strey/Desktop/Feature-models/releases/mappings), agora repousam **61 arquivos JSON** recém-saídos do forno, cada um contendo o resultado pormenorizado:
- A `version` em questão.
- O hash SHA-1 do `commit` exato (ou `null` caso as 3 heurísticas não tenham encontrado correspondência ou tenham estourado o tempo limite num histórico obscuro).
- O `status` final, o nome da heurística vencedora (`heuristic_description`) e o repositório consultado.

> [!TIP]
> **Próximos Passos**
> Os JSONs com as correlações (`Versão <-> Commit`) agora estão num formato excelente para consumo. Você pode alimentá-los de volta nos scripts do PowerShell de onde extraímos os dados (como no `extract_features.ps1`), ou usá-los nas ferramentas de predição do seu projeto de feature-models!
