# Prompt: Pipeline de Mapeamento de Releases Eclipse/simrel

## Contexto e Objetivo

Você é um engenheiro de software especialista em Python e pipelines de coleta de dados
científicos. Sua tarefa é implementar um **pipeline determinístico, auditável e
reproduzível** com dois estágios:

1. **Parte 1 — Extração:** Ler cada release do repositório `simrel.build` e extrair,
   para cada feature/contribuição, a versão declarada e o timestamp de build quando
   disponível.
2. **Parte 2 — Resolução:** Para cada (feature, versão) extraído, encontrar o commit
   SHA exato no repositório local daquela feature usando um sistema de heurísticas
   com votação por pesos.

Este pipeline será usado em pesquisa científica sobre **Line of Products Software
(LPS)**, portanto **reprodutibilidade e rastreabilidade são requisitos não
negociáveis**. Todo resultado deve ser auditável, e decisões ambíguas devem ser
logadas com justificativa explícita.

**Todos os repositórios já estão clonados localmente.** Nenhuma chamada de rede deve
ser feita durante a execução principal do pipeline — toda interação com git é feita
via `gitpython` sobre os clones locais.

---

## Repositórios Locais

```python
BASE_PATH = r"C:\Users\Kevin Strey\Desktop\Feature-models\1-Repositorios"

REPOSITORIES = {
    # chave = label usado no simrel, valor = nome da pasta dentro de BASE_PATH
    "simrel.build":      "simrel.build",
    "cdt":               "cdt",
    "gef-classic":       "gef-classic",
    "gef":               "gef-classic",          # mesmo repo, label diferente
    "org.eclipse.emf":   "org.eclipse.emf",
    "birt":              "birt",
    "datatools":         "datatools",
    "eclipselink":       "eclipselink",
    "egit":              "egit",
    "gmf-runtime":       "gmf-runtime",
    "org.eclipse.mylyn": "org.eclipse.mylyn",
    "org.eclipse.rap":   "org.eclipse.rap",
    "ptp":               "ptp",
    "scout.rt":          "scout.rt",
    "webtools.javaee":   "webtools.javaee",
    "windowbuilder":     "windowbuilder",
    "m2e-core":          "m2e-core",
}

def repo_path(name: str) -> Path:
    return Path(BASE_PATH) / REPOSITORIES[name]
```

---

## Formatos de Arquivo de Entrada

O `simrel.build` possui duas gerações de arquivos de contribuição, ambos XML:

### Formato antigo — `.b3aggrcon` (era Juno/Kepler, ~2012–2013)

```xml
<aggregator:Contribution xmlns:aggregator="http://www.eclipse.org/b3/2011/aggregator/1.1.0"
                         label="CDT">
  <repositories location="http://download.eclipse.org/tools/cdt/builds/juno/milestones"
                description="CDT updates">
    <features name="org.eclipse.cdt.feature.group"
              versionRange="8.0.0.201106081058">
      ...
    </features>
    <bundles name="org.eclipse.cdt.core.linux"
             versionRange="5.2.0.201106081058"/>
  </repositories>
</aggregator:Contribution>
```

**Características:**
- Versão explícita e precisa em `versionRange` em cada `<features>` e `<bundles>`
- Timestamp de build embutido na versão: `8.0.0.201106081058` → timestamp `201106081058`
- URL do repositório p2 presente em `location`, mas sem versão semântica nela

### Formato novo — `.aggrcon` (era Luna em diante, ~2014–atual)

```xml
<aggregator:Contribution xmlns:aggregator="http://www.eclipse.org/cbi/p2repo/2011/aggregator/1.1.0"
                         label="EMF (Core)">
  <repositories location="https://download.eclipse.org/modeling/emf/emf/builds/release/2.46.0"
                description="EMF 2.46">
    <features name="org.eclipse.emf.sdk.feature.group">
      ...
    </features>
  </repositories>
</aggregator:Contribution>
```

**Características:**
- Versão está **apenas na URL** do repositório p2 (`location`)
- `<features>` e `<bundles>` filhos **não têm** `versionRange`
- A URL pode conter apenas versão semântica (`/release/2.46.0`) ou versão + timestamp
  de build (`R-4.40-202606010713`)

---

## Parte 1 — Heurísticas de Extração do aggrcon

O parser XML deve identificar o formato pelo namespace do XML e aplicar a heurística
correspondente para extrair `(label, version, timestamp, p2_url)`.

### A1 — versionRange explícito (peso=10, formato `.b3aggrcon`)

**Quando usar:** namespace contém `b3` OU algum `<features>` possui atributo
`versionRange`.

**Como extrair:**
- `label` → atributo `label` da tag raiz `<aggregator:Contribution>`
- `version` → valor de `versionRange` da feature principal (a de maior especificidade,
  geralmente a que tem o nome mais curto, ex: `org.eclipse.cdt.feature.group`)
- `timestamp` → sufixo numérico da versão após o terceiro ponto:
  `"8.0.0.201106081058"` → `"201106081058"`
- `p2_url` → atributo `location` do `<repositories>`

```python
# Exemplo de resultado A1
{
    "label": "CDT",
    "version": "8.0.0.201106081058",
    "timestamp": "201106081058",   # sempre presente em A1
    "p2_url": "http://download.eclipse.org/tools/cdt/builds/juno/milestones",
    "extraction_heuristic": "A1",
    "extraction_weight": 10
}
```

### A2 — Versão semântica na URL (peso=6, formato `.aggrcon` simples)

**Quando usar:** namespace contém `cbi` E nenhum `<features>` possui `versionRange` E
a URL termina com um segmento de versão semântica (`/release/2.46.0`,
`/releases/4.2.0`).

**Como extrair:**
- `version` → último segmento de versão semântica da URL, via regex
  `r'(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)'` no path da URL
- `timestamp` → `None` (não disponível)
- `p2_url` → atributo `location` do `<repositories>`

```python
# Exemplo de resultado A2
{
    "label": "EMF (Core)",
    "version": "2.46.0",
    "timestamp": None,             # ausente em A2
    "p2_url": "https://download.eclipse.org/modeling/emf/emf/builds/release/2.46.0",
    "extraction_heuristic": "A2",
    "extraction_weight": 6
}
```

### A3 — Versão + timestamp na URL (peso=9, formato `.aggrcon` com build ID)

**Quando usar:** namespace contém `cbi` E a URL contém um segmento com padrão
`R-<versao>-<timestamp>` ou `S-<versao>-<timestamp>`.

**Como extrair:**
- `version` → grupo de versão do padrão, ex: `R-4.40-202606010713` → `"4.40"`
- `timestamp` → grupo de timestamp do padrão → `"202606010713"`
- `p2_url` → atributo `location` do `<repositories>`

```python
# Regex para A3:
pattern = r'[RS]-(\d+\.\d+(?:\.\d+)?)-(\d{12})'

# Exemplo de resultado A3
{
    "label": "Eclipse",
    "version": "4.40",
    "timestamp": "202606010713",   # presente em A3
    "p2_url": "https://download.eclipse.org/eclipse/updates/4.40/R-4.40-202606010713",
    "extraction_heuristic": "A3",
    "extraction_weight": 9
}
```

**Nota:** Quando múltiplos `<repositories>` existem no mesmo arquivo, processar cada
um como uma contribuição separada, mantendo o mesmo `label`.

---

## Parte 2 — Heurísticas de Resolução de Commit

Dado `(label, version, timestamp, repo_local_path)`, encontrar o commit SHA exato no
repositório local. Todas as operações usam `gitpython` sobre o clone local — sem
chamadas de rede.

As heurísticas votam com pesos. O commit com maior `vote_total_weight` vence. Quando
dois commits empatam, marcar como `NEEDS REVIEW`.

### H1 — Tag Match (baseado em nome da tag vs. versão extraída)

Listar todas as tags do repositório local via `repo.tags`. Para cada tag, aplicar as
variantes em ordem:

| Variante | Peso | Critério | Exemplo |
|---|---|---|---|
| H1-exact | 10 | dígitos da versão mapeiam exatamente para os dígitos da tag, independente de separadores | `CDT_8_1_0` ↔ `8.0.0` |
| H1-date-suffix | 9 | tag termina com `-YYYYMMDD` e a parte de versão bate | `1.5.0-20120612` |
| H1-date-prefix | 9 | tag começa com data e contém a versão como sufixo | `2011-12-12_S-3.8.0M4` |
| H1-loose | 7 | tag contém os dígitos da versão e a palavra "release" (case-insensitive) | `BIRT_4_2_0_Release_201206131143` |
| H1-partial | 6 | tag contém apenas major.minor da versão | `R4_2` ↔ `4.2.x` |

**Implementação do match de dígitos:**
```python
def digits_of(version: str) -> list[str]:
    """Extrai apenas os segmentos numéricos de uma versão.
    '8.0.0.201106081058' → ['8', '0', '0', '201106081058']
    '8.0.0' → ['8', '0', '0']
    """
    return re.findall(r'\d+', version.split('.')[0:4].__str__())
    # implementar corretamente separando por '.'

def tags_match_exact(tag_name: str, version: str) -> bool:
    """True se os dígitos principais da versão aparecem na tag na mesma ordem."""
    v_digits = re.findall(r'\d+', version)[:3]  # apenas major.minor.patch
    t_digits = re.findall(r'\d+', tag_name)
    # verifica se v_digits é subsequência de t_digits
    ...
```

O commit associado à tag é obtido via `tag.commit.hexsha` (ou
`tag.tag.object.hexsha` para tags anotadas).

### H4 — Maintenance Branch Time-Travel (peso=8)

**Requer:** `timestamp` disponível (extraído por A1 ou A3).

**Algoritmo:**
1. Listar todos os branches remotos do repo local: `repo.remote().refs`
2. Identificar branches de manutenção por padrão:
   `stable-X.Y`, `R<X>_<Y>_maintenance`, `maintenance/<X>.<Y>`,
   `<X>.<Y>.x`, `releases/<X>.<Y>`
3. Para cada branch de manutenção cuja versão bate com `major.minor` da feature:
   - Parsear `timestamp` como datetime: `datetime.strptime(ts, "%Y%m%d%H%M")`
   - Executar `git log <branch> --before="<datetime>" -1` via gitpython
   - Candidato = commit mais recente antes do timestamp naquele branch
4. Votar com peso 8 no commit encontrado

```python
MAINTENANCE_PATTERNS = [
    r'stable-(\d+)\.(\d+)',
    r'R(\d+)_(\d+)_maintenance',
    r'maintenance/(\d+)\.(\d+)',
    r'releases/(\d+)\.(\d+)',
    r'(\d+)\.(\d+)\.x',
]
```

### H0 — Timestamp Time-Travel (peso=6)

**Requer:** `timestamp` disponível (extraído por A1 ou A3).

**Algoritmo:**
1. Parsear `timestamp` como datetime
2. Via gitpython: iterar `repo.iter_commits(all=True, until=datetime, max_count=1)`
3. Candidato = commit mais recente em qualquer branch antes do timestamp
4. Votar com peso 6 no commit encontrado

**Nota:** H0 é o fallback mais amplo — usa todos os branches. Deve ser sempre
executado quando timestamp disponível, mesmo que H1 ou H4 já tenham votado.

### Regras de Votação e Status Final

```python
# Agregação
votes: dict[str, int] = {}  # commit_sha → peso acumulado
for heuristic_result in results:
    votes[heuristic_result.commit] += heuristic_result.weight

winner_sha = max(votes, key=votes.get)
vote_total_weight = votes[winner_sha]
vote_candidates = len(votes)

# Status
if vote_candidates == 0:
    status = "NOT FOUND"
elif vote_candidates > 5 or vote_total_weight < 6:
    status = "NEEDS REVIEW"
else:
    status = "SUCCESS"
```

---

## Schema de Saída

Um arquivo JSON por release, salvo em `output/<release_name>.json`:

```json
{
  "release": "JunoSR0",
  "simrel_commit": "abc123...",
  "mappings": {
    "CDT": {
      "version": "8.0.0.201106081058",
      "timestamp": "201106081058",
      "status": "SUCCESS",
      "commit": "502215b2868f940597b52feee0fd6d550558ffe3",
      "extraction_heuristic": "A1",
      "heuristic_id": "H1",
      "heuristic_description": "VOTE(H1(10)): H1 exact tag",
      "matched_value": "CDT_8_1_0",
      "repository": "cdt",
      "vote_total_weight": 10,
      "vote_candidates": 1
    },
    "EMF (Core)": {
      "version": "2.46.0",
      "timestamp": null,
      "status": "SUCCESS",
      "commit": "38c34011df71b95c983afaf720d31ccd9c2d0b33",
      "extraction_heuristic": "A2",
      "heuristic_id": "H1",
      "heuristic_description": "VOTE(H1(9)): H1 date-suffix tag",
      "matched_value": "R2_46_0",
      "repository": "org.eclipse.emf",
      "vote_total_weight": 9,
      "vote_candidates": 1
    },
    "WINDOWBUILDER": {
      "version": "1.2.0",
      "timestamp": null,
      "status": "NOT FOUND",
      "commit": null,
      "extraction_heuristic": "A2",
      "heuristic_id": null,
      "heuristic_description": null,
      "matched_value": null,
      "repository": null,
      "vote_total_weight": 0,
      "vote_candidates": 0
    }
  }
}
```

**Campo adicional obrigatório:**
- `simrel_commit`: SHA do commit do `simrel.build` de onde esta release foi lida —
  garante reprodutibilidade total da fonte

---

## Arquitetura do Pipeline

```
simrel_mapper/
├── main.py                        # entrypoint CLI
├── config.py                      # BASE_PATH, REPOSITORIES, constantes
├── models.py                      # Pydantic: ExtractionResult, MappingResult, ReleaseOutput
│
├── ingestion/
│   ├── simrel_reader.py           # itera commits/tags do simrel.build via gitpython
│   │                              # identifica cada release pelo nome do commit/tag
│   └── aggrcon_parser.py          # parser XML dos .aggrcon e .b3aggrcon
│                                  # aplica A1, A2, A3 e retorna lista de ExtractionResult
│
├── heuristics/
│   ├── base.py                    # classe abstrata Heuristic(vote() → HeuristicVote | None)
│   ├── h1_tag_match.py            # variantes H1-exact, H1-date-suffix, H1-date-prefix,
│   │                              # H1-loose, H1-partial usando repo.tags local
│   ├── h4_branch_travel.py        # H4: branch de manutenção + timestamp via gitpython
│   ├── h0_timestamp.py            # H0: time-travel global via gitpython
│   └── engine.py                  # VotingEngine: agrega votos, decide status
│
├── output/                        # JSONs gerados, um por release
│   └── JunoSR0.json
│
├── audit/
│   └── logger.py                  # structlog: log estruturado por release/feature/heurística
│
└── tests/
    ├── ground_truth/
    │   └── JunoSR0.json           # ground truth para regressão
    ├── fixtures/
    │   ├── cdt.b3aggrcon          # arquivo real para testar parser
    │   ├── emf-emf.aggrcon        # arquivo real para testar parser
    │   └── ep.aggrcon             # arquivo real para testar parser
    ├── test_regression.py         # pipeline completo vs. ground truth
    ├── test_aggrcon_parser.py     # testa A1, A2, A3 com os fixtures reais
    └── test_heuristics.py         # testa cada heurística H0, H1, H4 com casos unitários
```

---

## Requisitos de Implementação

### 1. simrel_reader.py

O `simrel.build` organiza releases como **tags git** ou como **commits nomeados**.
Usar gitpython para listar todas as tags e commits do repositório local em
`BASE_PATH/simrel.build`:

```python
import git

def iter_releases(simrel_repo_path: Path) -> Iterator[ReleaseRef]:
    """
    Itera todas as releases do simrel.build em ordem cronológica.
    Cada release é identificada por uma tag ou por um padrão no commit message.
    Retorna ReleaseRef(name, commit_sha, tree) onde tree permite acessar
    os arquivos .aggrcon/.b3aggrcon daquela release.
    """
    repo = git.Repo(simrel_repo_path)
    for tag in sorted(repo.tags, key=lambda t: t.commit.committed_date):
        yield ReleaseRef(
            name=tag.name,
            commit_sha=tag.commit.hexsha,
            tree=tag.commit.tree
        )
```

Para acessar os arquivos `.aggrcon`/`.b3aggrcon` de uma release sem fazer checkout:
```python
# Listar arquivos da release diretamente da tree
for blob in release_ref.tree.traverse():
    if blob.name.endswith(('.aggrcon', '.b3aggrcon')):
        content = blob.data_stream.read().decode('utf-8')
        parse_aggrcon(content, blob.name)
```

### 2. aggrcon_parser.py

```python
from xml.etree import ElementTree as ET

NAMESPACE_B3  = "http://www.eclipse.org/b3/2011/aggregator/1.1.0"
NAMESPACE_CBI = "http://www.eclipse.org/cbi/p2repo/2011/aggregator/1.1.0"

def parse_aggrcon(xml_content: str, filename: str) -> list[ExtractionResult]:
    """
    Detecta o namespace e aplica A1, A2 ou A3.
    Retorna lista (pode ser >1 se houver múltiplos <repositories>).
    Nunca lança exceção — erros retornam ExtractionResult com status=PARSE_ERROR.
    """
    root = ET.fromstring(xml_content)
    namespace = detectar_namespace(root)

    if namespace == NAMESPACE_B3 or tem_version_range(root):
        return extrair_A1(root, filename)
    else:
        return extrair_A2_ou_A3(root, filename)
```

**Regra de prioridade quando A1 e A2/A3 conflitam no mesmo arquivo:**
- Se qualquer `<features>` tem `versionRange` → usar A1, ignorar URL para versão
- Caso contrário → A2 ou A3 baseado na URL

### 3. VotingEngine

```python
@dataclass
class HeuristicVote:
    commit_sha: str
    heuristic_id: str
    heuristic_variant: str     # ex: "H1-exact", "H1-date-suffix"
    weight: int
    matched_value: str         # o que foi encontrado: nome da tag, nome do branch, etc.

class VotingEngine:
    HEURISTICS = [H1TagMatch, H4BranchTravel, H0TimestampTravel]

    def resolve(
        self,
        repo_path: Path,
        version: str,
        timestamp: str | None,
        label: str
    ) -> MappingResult:
        repo = git.Repo(repo_path)
        all_votes: list[HeuristicVote] = []

        for HClass in self.HEURISTICS:
            h = HClass(repo)
            vote = h.vote(version=version, timestamp=timestamp)
            if vote:
                all_votes.append(vote)

        return self._aggregate(all_votes, label, version, timestamp)

    def _aggregate(self, votes, label, version, timestamp) -> MappingResult:
        if not votes:
            return MappingResult(status="NOT FOUND", ...)

        # agrupar por commit_sha e somar pesos
        tally: dict[str, int] = defaultdict(int)
        for v in votes:
            tally[v.commit_sha] += v.weight

        winner_sha = max(tally, key=tally.get)
        winner_votes = [v for v in votes if v.commit_sha == winner_sha]
        vote_candidates = len(tally)
        vote_total_weight = tally[winner_sha]

        # heuristic_description: lista as heurísticas que votaram no vencedor
        desc = " + ".join(f"{v.heuristic_variant}({v.weight})" for v in winner_votes)
        heuristic_description = f"VOTE({desc})"

        status = "SUCCESS"
        if vote_candidates > 5 or vote_total_weight < 6:
            status = "NEEDS REVIEW"

        return MappingResult(
            status=status,
            commit=winner_sha,
            heuristic_id=winner_votes[0].heuristic_id,
            heuristic_description=heuristic_description,
            matched_value=winner_votes[0].matched_value,
            vote_total_weight=vote_total_weight,
            vote_candidates=vote_candidates,
        )
```

### 4. Acesso ao git — Regras Obrigatórias

- **Proibido:** `subprocess`, `os.system`, chamadas shell diretas
- **Obrigatório:** usar exclusivamente `gitpython` (`import git`)
- **Proibido:** `git.remote().fetch()`, `git.remote().pull()` ou qualquer operação
  de rede — os repos já estão clonados e atualizados
- **Proibido:** `repo.git.checkout()` — acessar conteúdo de commits via `tree` e
  `blob.data_stream`, nunca modificando o working directory
- Tags locais são acessadas via `repo.tags`
- Branches remotos (já baixados) via `repo.remote('origin').refs`
- Iterar commits de um branch: `repo.iter_commits('origin/stable-2.0')`
- Commit mais recente antes de um datetime:
  ```python
  list(repo.iter_commits('--all', until=dt, max_count=1))[0]
  ```

### 5. Reprodutibilidade

- Cada JSON de saída inclui `simrel_commit` — o SHA exato do commit do `simrel.build`
  de onde a release foi lida
- Os JSONs de saída são o artefato final — não há banco intermediário
- Um JSON já existente em `output/` não é sobrescrito por padrão (usar flag
  `--force` para reprocessar)
- Os arquivos de fixture em `tests/fixtures/` são cópias exatas dos `.aggrcon`
  reais — commitar junto ao código

---

## Dependências (requirements.txt)

```
gitpython>=3.1.40
pydantic>=2.5.0
structlog>=24.1.0
rich>=13.7.0
pytest>=8.0.0
python-dotenv>=1.0.0
```

**Nota:** Sem PyGithub, sem httpx, sem SQLAlchemy — toda interação é local via
gitpython. A biblioteca padrão `xml.etree.ElementTree` é suficiente para o parser XML.

---

## CLI (main.py)

```
python main.py run --all
    Processa todas as 62 releases do simrel.build. Pula releases já existentes
    em output/ (usar --force para reprocessar).

python main.py run --release JunoSR0
    Processa uma release específica pelo nome da tag.

python main.py run --from Juno --to Mars
    Processa releases em um intervalo de nomes (ordem cronológica).

python main.py review
    Lista todos os mapeamentos com status=NEEDS_REVIEW de todos os JSONs em output/.
    Formato tabular com release, feature, version, vote_candidates, vote_total_weight.

python main.py stats
    Distribuição de heurísticas (A1/A2/A3 e H0/H1/H4) e taxa de cobertura
    agregadas sobre todos os JSONs em output/.

python main.py test
    Executa pytest nos testes de regressão.
```

---

## Logging e Auditoria

```
[INFO]  release=JunoSR0 feature=CDT  extraction=A1 version=8.0.0.201106081058 timestamp=201106081058
[INFO]  release=JunoSR0 feature=CDT  H1-exact tag=CDT_8_1_0 commit=502215b... weight=10
[INFO]  release=JunoSR0 feature=CDT  H0 timestamp=201106081058 commit=502215b... weight=6
[INFO]  release=JunoSR0 feature=CDT  WINNER commit=502215b... total_weight=16 candidates=1 status=SUCCESS
[WARN]  release=JunoSR0 feature=EMF  vote_candidates=2 pesos=[10,6] → usando maior peso, verificar manualmente
[ERROR] release=JunoSR0 feature=WINDOWBUILDER nenhuma heurística retornou voto → NOT FOUND
```

---

## Restrições e Boas Práticas

1. **Sem rede:** nenhuma chamada HTTP, fetch ou pull — apenas leitura dos repos locais
2. **Sem checkout:** acessar conteúdo de commits via `blob.data_stream`, nunca via
   `repo.git.checkout()`
3. **Falhas isoladas:** erro em uma feature não interrompe o processamento das demais
4. **JSONs são a fonte de verdade:** gerados diretamente, sem banco intermediário
5. **Idempotente:** reprocessar uma release deve produzir exatamente o mesmo JSON
6. **Type hints** em todas as funções públicas
7. **Docstrings** em todas as classes e métodos públicos
8. **Sem credenciais hardcoded:** `BASE_PATH` pode ser configurado via `.env`

---

## Ordem de Implementação Recomendada

1. `models.py` — Pydantic models: `ExtractionResult`, `HeuristicVote`,
   `MappingResult`, `ReleaseOutput`
2. `ingestion/aggrcon_parser.py` + `tests/test_aggrcon_parser.py` usando os três
   fixtures reais (cdt.b3aggrcon, emf-emf.aggrcon, ep.aggrcon) — validar A1, A2, A3
3. `ingestion/simrel_reader.py` — iterar releases via gitpython sem checkout
4. `heuristics/h1_tag_match.py` + testes unitários com tags reais do repo CDT local
5. `heuristics/h4_branch_travel.py` + testes com branches reais do repo EGIT local
6. `heuristics/h0_timestamp.py` + testes com repo GEF local (que usa H0 no ground truth)
7. `heuristics/engine.py` — VotingEngine integrando H0+H1+H4
8. `main.py` — CLI orquestrando Parte 1 + Parte 2 + escrita dos JSONs
9. `tests/test_regression.py` — validação final completa contra JunoSR0