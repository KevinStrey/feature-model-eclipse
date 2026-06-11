# Pipeline de Mapeamento de Releases Eclipse/simrel

Pipeline Python determinístico e auditável que mapeia releases do `simrel.build` para commit SHAs dos repositórios de features. Dois estágios: **Extração** (parse XML → versão/timestamp) e **Resolução** (heurísticas com votação → commit SHA).

## Dados do Ambiente (verificados)

| Item | Valor |
|---|---|
| Python | 3.14.5 |
| Tags no simrel.build | 61 (JunoSR0 → 2026-03) |
| Repositórios locais | 19 pastas em `1-Repositorios/` |
| Formato antigo | `.b3aggrcon` — namespace `b3`, `versionRange` explícito (JunoSR0: 67 arquivos) |
| Formato novo | `.aggrcon` — namespace `cbi`, versão na URL (2026-03: ~35 arquivos) |
| Tag naming CDT | `CDT_10_0_0`, `CDT_11_1_0`, etc. |
| Tag naming EMF | `R2_10_0`, `R2_45_0`, etc. |

---

## Proposed Changes

### Phase 1 — Project Setup

#### [NEW] [requirements.txt](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/requirements.txt)
- `gitpython>=3.1.40`, `pydantic>=2.5.0`, `structlog>=24.1.0`, `rich>=13.7.0`, `pytest>=8.0.0`, `python-dotenv>=1.0.0`

#### [NEW] [config.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/config.py)
- `BASE_PATH` loaded from `.env` or default
- `REPOSITORIES` dict (label → folder name), exactly as specified in prompt
- `OUTPUT_DIR`, `AUDIT_DIR` paths
- `repo_path(name)` helper

---

### Phase 2 — Pydantic Data Models

#### [NEW] [models.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/models.py)

| Model | Purpose |
|---|---|
| `ReleaseRef` | `name`, `commit_sha`, reference to git tree object |
| `ExtractionResult` | `label`, `version`, `timestamp`, `p2_url`, `extraction_heuristic` (A1/A2/A3), `extraction_weight`, `filename` |
| `HeuristicVote` | `commit_sha`, `heuristic_id` (H0/H1/H4), `heuristic_variant` (e.g. H1-exact), `weight`, `matched_value` |
| `MappingResult` | `version`, `timestamp`, `status`, `commit`, `extraction_heuristic`, `heuristic_id`, `heuristic_description`, `matched_value`, `repository`, `vote_total_weight`, `vote_candidates` |
| `ReleaseOutput` | `release`, `simrel_commit`, `mappings: dict[str, MappingResult]` — serialized to JSON |

- `ReleaseRef.tree` will use `Any` type annotation since it holds a gitpython `Tree` object

---

### Phase 3 — XML Parser (Ingestion)

#### [NEW] [ingestion/__init__.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/ingestion/__init__.py)
Empty init.

#### [NEW] [ingestion/aggrcon_parser.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/ingestion/aggrcon_parser.py)

**Core logic:**

1. `parse_aggrcon(xml_content, filename) → list[ExtractionResult]`
   - Detects namespace from root element attributes
   - Routes to A1, A2, or A3 extraction
   - Never raises — wraps errors in `ExtractionResult(status="PARSE_ERROR")`

2. **A1 — versionRange** (weight=10):
   - Triggered when namespace contains `b3` OR any `<features>` has `versionRange`
   - Extracts `label` from root `label` attribute
   - For version: picks the feature with `versionRange` that has the shortest `name` (most specific)
   - Extracts timestamp from version qualifier: `8.0.0.201106081058` → `201106081058`
   - Real example verified: `cdt.b3aggrcon` from JunoSR0

3. **A2 — Semantic version in URL** (weight=6):
   - Triggered when namespace contains `cbi`, no `versionRange` present, URL has semver segment
   - Regex: `r'(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)'` applied to URL path
   - `timestamp = None`
   - Real example verified: `emf-emf.aggrcon` from 2026-03 → version `2.45.0`

4. **A3 — Version + timestamp in URL** (weight=9):
   - Triggered when URL contains `R-<ver>-<ts>` or `S-<ver>-<ts>` pattern
   - Regex: `r'[RS]-(\d+\.\d+(?:\.\d+)?)-(\d{12})'`
   - Real example verified: `ep.aggrcon` from 2026-03 → `R-4.39-202602260420`

5. **Priority rule**: A3 checked before A2 (if URL matches A3 pattern, A3 wins over A2)

**Edge cases observed in real data:**
- Some `<bundles>` in new format have `versionRange` as a range constraint like `[1.0.0,2.0.0)` — these are **NOT** A1 version ranges (they're dependency constraints). Must only count exact versions (no brackets).
- Multiple `<repositories>` per file → each becomes a separate `ExtractionResult`, same `label`

---

### Phase 4 — Simrel Reader

#### [NEW] [ingestion/simrel_reader.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/ingestion/simrel_reader.py)

- `iter_releases(simrel_repo_path) → Iterator[ReleaseRef]`
  - Opens repo via `git.Repo(path)`
  - Iterates `repo.tags` sorted by `tag.commit.committed_date`
  - Yields `ReleaseRef(name=tag.name, commit_sha=tag.commit.hexsha, tree=tag.commit.tree)`

- `get_aggrcon_files(tree) → Iterator[tuple[str, str]]`
  - Traverses tree via `tree.traverse()`
  - Yields `(blob.name, blob.data_stream.read().decode('utf-8'))` for `.aggrcon`/`.b3aggrcon` files

- `get_release_by_name(simrel_repo_path, name) → ReleaseRef | None`
  - Finds a specific tag by name

---

### Phase 5 — Heuristics

#### [NEW] [heuristics/__init__.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/heuristics/__init__.py)

#### [NEW] [heuristics/base.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/heuristics/base.py)
- Abstract `Heuristic` class with `vote(version, timestamp) → list[HeuristicVote]`
- Helper `digits_of(version)` — extracts numeric segments
- Helper `resolve_tag_commit(tag)` — handles both lightweight and annotated tags

#### [NEW] [heuristics/h1_tag_match.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/heuristics/h1_tag_match.py)

Iterates all `repo.tags` and applies variants in priority order:

| Variant | Weight | Logic |
|---|---|---|
| H1-exact | 10 | `digits_of(tag)[:3] == digits_of(version)[:3]` — e.g. `CDT_8_0_0` ↔ `8.0.0` |
| H1-date-suffix | 9 | Tag ends with `-YYYYMMDD`, version part matches |
| H1-date-prefix | 9 | Tag starts with date pattern and contains version as suffix |
| H1-loose | 7 | Tag contains version digits AND "release" (case-insensitive) |
| H1-partial | 6 | Tag contains only major.minor of the version — e.g. `R4_2` ↔ `4.2.x` |

- Returns **all matching votes** (one per matching tag variant), not just the first
- `resolve_tag_commit()` peels annotated tags to get the actual commit

#### [NEW] [heuristics/h4_branch_travel.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/heuristics/h4_branch_travel.py)

- **Requires** `timestamp` (from A1 or A3)
- Lists remote refs via `repo.remote('origin').refs`
- Matches branch names against `MAINTENANCE_PATTERNS`:
  - `stable-X.Y`, `RX_Y_maintenance`, `maintenance/X.Y`, `releases/X.Y`, `X.Y.x`
- For matching branches: `repo.iter_commits(branch, until=parsed_datetime, max_count=1)`
- Weight = 8

#### [NEW] [heuristics/h0_timestamp.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/heuristics/h0_timestamp.py)

- **Requires** `timestamp`
- Parses timestamp → datetime
- `repo.iter_commits('--all', until=dt, max_count=1)`
- Weight = 6
- Always runs as fallback when timestamp available

---

### Phase 6 — Voting Engine

#### [NEW] [heuristics/engine.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/heuristics/engine.py)

- `VotingEngine.resolve(repo_path, version, timestamp, label) → MappingResult`
- Runs H1, H4, H0 in sequence, collects all `HeuristicVote`s
- Aggregates by `commit_sha`, sums weights
- Winner = max total weight
- Status rules:
  - 0 candidates → `NOT FOUND`
  - >5 candidates OR total_weight < 6 → `NEEDS REVIEW`
  - Otherwise → `SUCCESS`
- `heuristic_description` = `"VOTE(H1-exact(10) + H0(6))"` showing all winning votes

---

### Phase 7 — Audit Logger

#### [NEW] [audit/__init__.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/audit/__init__.py)

#### [NEW] [audit/logger.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/audit/logger.py)
- Configures `structlog` with JSON + console renderers
- `get_logger(release, feature)` — bound logger with context
- Log levels per prompt spec:
  - INFO: extraction result, each heuristic vote, final winner
  - WARN: ties or borderline decisions
  - ERROR: NOT FOUND results

---

### Phase 8 — CLI (main.py)

#### [NEW] [main.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/main.py)

Uses `argparse` with subcommands:

| Command | Description |
|---|---|
| `run --all` | Process all 61 releases. Skips existing JSONs (use `--force`) |
| `run --release NAME` | Process single release |
| `run --from NAME --to NAME` | Process range (chronological) |
| `review` | List all `NEEDS REVIEW` mappings across output JSONs (rich table) |
| `stats` | Heuristic distribution and coverage stats (rich table) |
| `test` | Runs pytest |

**Pipeline orchestration in `run`:**
1. Open simrel.build repo
2. Iterate releases (filtered by args)
3. For each release:
   - Traverse tree → find `.aggrcon`/`.b3aggrcon` blobs
   - Parse each blob → `ExtractionResult`s
   - Map label → local repo path via `REPOSITORIES` dict
   - For each extraction: run `VotingEngine.resolve()` → `MappingResult`
   - Assemble `ReleaseOutput` with `simrel_commit`
   - Write JSON to `output/<release_name>.json`
4. Failures in one feature don't stop others (try/except per feature)

---

### Phase 9 — Tests

#### [NEW] [tests/fixtures/](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/tests/fixtures/)
- `cdt.b3aggrcon` — real file from JunoSR0 tag
- `emf-emf.aggrcon` — real file from 2026-03 tag
- `ep.aggrcon` — real file from 2026-03 tag

#### [NEW] [tests/test_aggrcon_parser.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/tests/test_aggrcon_parser.py)
- Test A1 with cdt.b3aggrcon → expects version `8.0.0.201106081058`, timestamp `201106081058`
- Test A2 with emf-emf.aggrcon → expects version `2.45.0`, timestamp `None`
- Test A3 with ep.aggrcon → expects version `4.39`, timestamp `202602260420`
- Test edge case: bundles with range constraint `[1.0.0,2.0.0)` not treated as A1

#### [NEW] [tests/test_heuristics.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/tests/test_heuristics.py)
- H1 tests against real CDT repo tags
- H4 tests against real egit repo branches
- H0 tests with timestamp against real repos

#### [NEW] [tests/test_regression.py](file:///c:/Users/Kevin Strey/Desktop/Feature-models/3-Mapeamento_features_simrel/simrel_mapper/tests/test_regression.py)
- Full pipeline run for JunoSR0
- Compare against ground truth JSON

---

## Open Questions

> [!IMPORTANT]
> **Label-to-repo mapping coverage**: The `REPOSITORIES` dict has 16 entries, but simrel.build JunoSR0 has 67 `.b3aggrcon` files (e.g., `dltk`, `ecf`, `linuxtools`, `pdt`, etc.). Features whose labels don't match any key in `REPOSITORIES` will be skipped. Should these be:
> - (a) Logged as `NOT FOUND` with `repository: null` and included in the output JSON?
> - (b) Silently skipped?
> - (c) Should I expand the REPOSITORIES dict to cover more of them?

> [!IMPORTANT]
> **Handling version range constraints in new format**: The `ep.aggrcon` file (new format) has bundles with `versionRange="[1.0.0,2.0.0)"` — these are dependency range constraints, not exact versions. The prompt says "if any `<features>` has `versionRange` → use A1". Should bundles with range constraints (containing `[` or `)`) be excluded from this check, only counting `<features>` with exact versions?

---

## Verification Plan

### Automated Tests
```bash
cd simrel_mapper
pip install -r requirements.txt
pytest tests/ -v
```

### Manual Verification
1. Run `python main.py run --release JunoSR0` and inspect output JSON
2. Run `python main.py run --release 2026-03` and inspect for A2/A3 outputs
3. Run `python main.py review` to check any `NEEDS REVIEW` entries
4. Run `python main.py stats` for distribution overview
5. Spot-check: verify a CDT commit SHA from output matches `git show <sha>` in the CDT repo
