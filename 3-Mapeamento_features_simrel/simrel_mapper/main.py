"""
CLI principal do pipeline simrel_mapper.

Subcomandos:
    run      — processa releases do simrel.build
    review   — lista mapeamentos com status NEEDS REVIEW
    stats    — distribuição de heurísticas e taxa de cobertura
    test     — executa pytest
"""

from __future__ import annotations

import argparse
import git
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table

from audit.logger import configure_logging, get_logger
from config import OUTPUT_DIR, REPOSITORIES, repo_path, simrel_repo_path
from heuristics.engine import VotingEngine
from ingestion.aggrcon_parser import parse_aggrcon
from ingestion.simrel_reader import (
    get_release_by_name,
    get_releases_in_range,
    iter_aggrcon_blobs,
    iter_releases,
)
from models import MappingResult, ReleaseOutput

console = Console()


# ---------------------------------------------------------------------------
# Mapeamento de label → chave do REPOSITORIES
# ---------------------------------------------------------------------------

def _find_repo_key(label: str) -> str | None:
    """Tenta encontrar a chave do REPOSITORIES que corresponde ao label.

    O match é case-insensitive e tenta variações comuns:
    - label exato
    - label em minúsculas
    - label com prefixo 'org.eclipse.'
    - label convertendo espaços e parênteses
    """
    label_lower = label.lower().strip()

    # Match exato
    if label_lower in REPOSITORIES:
        return label_lower

    # Tentar variações
    for key in REPOSITORIES:
        key_lower = key.lower()
        # label "CDT" → key "cdt"
        if label_lower == key_lower:
            return key
        # Permite match de prefixo longo: label "WebTools 3.12..." → key "webtools"
        if label_lower.startswith(key_lower):
            return key
        # label "EMF (Core)" → key contém "emf"
        # Extrair apenas letras/números do label
        label_clean = "".join(c for c in label_lower if c.isalnum())
        key_clean = "".join(c for c in key_lower if c.isalnum())
        if label_clean == key_clean:
            return key

    return None


# ---------------------------------------------------------------------------
# Subcomando: run
# ---------------------------------------------------------------------------


def _process_release(
    release_name: str,
    simrel_commit: str,
    tree,
    engine: VotingEngine,
    force: bool,
) -> ReleaseOutput | None:
    """Processa uma release individual.

    Returns:
        ReleaseOutput se processado com sucesso, None se já existe e --force não foi dado.
    """
    log = get_logger(release=release_name)
    output_file = OUTPUT_DIR / f"{release_name}.json"

    if output_file.exists() and not force:
        log.info("skipped", reason="already exists", path=str(output_file))
        return None

    log.info("processing_release", commit=simrel_commit[:12])

    try:
        simrel_repo_obj = git.Repo(str(simrel_repo_path()))
        simrel_date = simrel_repo_obj.commit(simrel_commit).committed_datetime
    except Exception as e:
        with open('debug_simrel_date.txt', 'w') as f:
            f.write(f"Exception: {type(e).__name__} - {str(e)}\n")
        log.error("simrel_date_error", error=str(e), commit=simrel_commit)
        simrel_date = None

    mappings: dict[str, MappingResult] = {}
    seen_labels: set[str] = set()

    for filename, xml_content in iter_aggrcon_blobs(tree):
        try:
            extractions = parse_aggrcon(xml_content, filename)
        except Exception as exc:
            log.error("parse_error", filename=filename, error=str(exc))
            continue

        for ext in extractions:
            if ext.extraction_heuristic == "PARSE_ERROR":
                log.error("parse_error", filename=filename, label=ext.label)
                continue

            if ext.version is None:
                log.warning("no_version", filename=filename, label=ext.label)
                # NOT CONTINUE! Allow heuristics to fallback or find other ways.

            # Evitar duplicação de labels (pegar a primeira ocorrência com versão)
            if ext.label in seen_labels:
                continue
            seen_labels.add(ext.label)

            log.info(
                "extraction",
                extraction=ext.extraction_heuristic,
                version=ext.version,
                timestamp=ext.timestamp,
                label=ext.label,
            )

            # Bifurcar a extração da plataforma para JDT e PDE
            labels_to_evaluate = [ext.label]
            if ext.label.lower() in ("eclipse", "eclipse platform", "eclipse sdk"):
                labels_to_evaluate.extend(["JDT", "PDE", "CVS"])
            if "webtools" in ext.label.lower() or "web tools" in ext.label.lower():
                labels_to_evaluate.extend(["EclipseLink"])

            for label in labels_to_evaluate:
                # Encontrar repositório local correspondente
                repo_key = _find_repo_key(label)
                if repo_key is None:
                    # Silenciosamente pular features sem repo local (conforme decisão do usuário)
                    continue

                try:
                    local_repo = repo_path(repo_key)
                except KeyError:
                    continue

                if not local_repo.exists():
                    log.warning("repo_missing", label=label, path=str(local_repo))
                    continue

                # Resolver commit via votação
                try:
                    mapping = engine.resolve(
                        repo_path=local_repo,
                        version=ext.version,
                        timestamp=ext.timestamp,
                        label=label,
                        release_name=release_name,
                        simrel_date=simrel_date,
                    )
                    mapping.extraction_heuristic = ext.extraction_heuristic
                    mappings[label] = mapping
                except Exception as exc:
                    log.error(
                        "resolve_error",
                        label=label,
                        version=ext.version,
                        error=str(exc),
                    )
                    mappings[label] = MappingResult(
                        version=ext.version,
                        timestamp=ext.timestamp,
                        status="NOT FOUND",
                        extraction_heuristic=ext.extraction_heuristic,
                        repository=repo_key,
                )

    output = ReleaseOutput(
        release=release_name,
        simrel_commit=simrel_commit,
        mappings=mappings,
    )

    # Salvar JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        output.model_dump_json(indent=2),
        encoding="utf-8",
    )
    log.info(
        "release_complete",
        features_mapped=len(mappings),
        output=str(output_file),
    )

    return output


def cmd_run(args: argparse.Namespace) -> None:
    """Executa o pipeline para as releases selecionadas."""
    configure_logging()
    engine = VotingEngine()
    simrel_path = simrel_repo_path()

    if args.release:
        # Processar uma release específica
        ref = get_release_by_name(simrel_path, args.release)
        if ref is None:
            console.print(f"[red]Release '{args.release}' não encontrada.[/red]")
            sys.exit(1)
        _process_release(ref.name, ref.commit_sha, ref.tree, engine, args.force)

    elif args.all:
        # Processar todas
        releases = list(iter_releases(simrel_path))
        console.print(f"[bold]Processando {len(releases)} releases...[/bold]")
        for i, ref in enumerate(releases, 1):
            console.print(
                f"[dim][{i}/{len(releases)}][/dim] {ref.name}",
                end=" ",
            )
            result = _process_release(
                ref.name, ref.commit_sha, ref.tree, engine, args.force
            )
            if result:
                success = sum(
                    1 for m in result.mappings.values() if m.status == "SUCCESS"
                )
                total = len(result.mappings)
                console.print(f"[green]{success}/{total} SUCCESS[/green]")
            else:
                console.print("[yellow]SKIPPED[/yellow]")

    elif args.from_release or args.to_release:
        # Processar intervalo
        releases = get_releases_in_range(
            simrel_path, args.from_release, args.to_release
        )
        console.print(f"[bold]Processando {len(releases)} releases no intervalo...[/bold]")
        for i, ref in enumerate(releases, 1):
            console.print(
                f"[dim][{i}/{len(releases)}][/dim] {ref.name}",
                end=" ",
            )
            result = _process_release(
                ref.name, ref.commit_sha, ref.tree, engine, args.force
            )
            if result:
                success = sum(
                    1 for m in result.mappings.values() if m.status == "SUCCESS"
                )
                total = len(result.mappings)
                console.print(f"[green]{success}/{total} SUCCESS[/green]")
            else:
                console.print("[yellow]SKIPPED[/yellow]")

    else:
        console.print("[red]Especifique --all, --release ou --from/--to.[/red]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subcomando: review
# ---------------------------------------------------------------------------


def cmd_review(args: argparse.Namespace) -> None:
    """Lista todos os mapeamentos com status NEEDS REVIEW."""
    if not OUTPUT_DIR.exists():
        console.print("[red]Diretório output/ não encontrado.[/red]")
        return

    table = Table(title="Mapeamentos — NEEDS REVIEW", show_lines=True)
    table.add_column("Release", style="bold")
    table.add_column("Feature")
    table.add_column("Version")
    table.add_column("Candidates", justify="right")
    table.add_column("Total Weight", justify="right")
    table.add_column("Description")

    count = 0
    for json_file in sorted(OUTPUT_DIR.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        release_name = data.get("release", json_file.stem)
        for label, mapping in data.get("mappings", {}).items():
            if mapping.get("status") == "NEEDS REVIEW":
                table.add_row(
                    release_name,
                    label,
                    mapping.get("version", ""),
                    str(mapping.get("vote_candidates", 0)),
                    str(mapping.get("vote_total_weight", 0)),
                    mapping.get("heuristic_description", ""),
                )
                count += 1

    console.print(table)
    console.print(f"\n[bold]{count}[/bold] mapeamentos necessitam revisão.")


# ---------------------------------------------------------------------------
# Subcomando: stats
# ---------------------------------------------------------------------------


def cmd_stats(args: argparse.Namespace) -> None:
    """Mostra distribuição de heurísticas e taxa de cobertura."""
    if not OUTPUT_DIR.exists():
        console.print("[red]Diretório output/ não encontrado.[/red]")
        return

    extraction_counter: Counter = Counter()
    heuristic_counter: Counter = Counter()
    status_counter: Counter = Counter()
    total_mappings = 0

    for json_file in sorted(OUTPUT_DIR.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for label, mapping in data.get("mappings", {}).items():
            total_mappings += 1
            extraction_counter[mapping.get("extraction_heuristic", "?")] += 1
            status_counter[mapping.get("status", "?")] += 1
            h_id = mapping.get("heuristic_id")
            if h_id:
                heuristic_counter[h_id] += 1

    # Tabela de extração
    table_ext = Table(title="Distribuição — Heurísticas de Extração")
    table_ext.add_column("Heurística")
    table_ext.add_column("Count", justify="right")
    table_ext.add_column("%", justify="right")
    for h, c in extraction_counter.most_common():
        pct = f"{c / total_mappings * 100:.1f}" if total_mappings else "0"
        table_ext.add_row(h, str(c), pct)
    console.print(table_ext)

    # Tabela de resolução
    table_res = Table(title="Distribuição — Heurísticas de Resolução")
    table_res.add_column("Heurística")
    table_res.add_column("Count", justify="right")
    table_res.add_column("%", justify="right")
    for h, c in heuristic_counter.most_common():
        pct = f"{c / total_mappings * 100:.1f}" if total_mappings else "0"
        table_res.add_row(h, str(c), pct)
    console.print(table_res)

    # Tabela de status
    table_status = Table(title="Distribuição — Status")
    table_status.add_column("Status")
    table_status.add_column("Count", justify="right")
    table_status.add_column("%", justify="right")
    for s, c in status_counter.most_common():
        pct = f"{c / total_mappings * 100:.1f}" if total_mappings else "0"
        table_status.add_row(s, str(c), pct)
    console.print(table_status)

    console.print(f"\n[bold]Total de mapeamentos:[/bold] {total_mappings}")
    console.print(
        f"[bold]Releases processadas:[/bold] "
        f"{len(list(OUTPUT_DIR.glob('*.json')))}"
    )


# ---------------------------------------------------------------------------
# Subcomando: test
# ---------------------------------------------------------------------------


def cmd_test(args: argparse.Namespace) -> None:
    """Executa pytest nos testes."""
    test_dir = Path(__file__).parent / "tests"
    subprocess.run(
        [sys.executable, "-m", "pytest", str(test_dir), "-v"],
        cwd=str(Path(__file__).parent),
    )


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        prog="simrel_mapper",
        description="Pipeline de mapeamento de releases Eclipse/simrel para commits.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcomandos disponíveis")

    # run
    p_run = subparsers.add_parser("run", help="Processa releases do simrel.build")
    p_run.add_argument("--all", action="store_true", help="Processar todas as releases")
    p_run.add_argument("--release", type=str, help="Processar uma release específica")
    p_run.add_argument(
        "--from", dest="from_release", type=str, help="Release inicial do intervalo"
    )
    p_run.add_argument(
        "--to", dest="to_release", type=str, help="Release final do intervalo"
    )
    p_run.add_argument(
        "--force", action="store_true", help="Reprocessar releases já existentes"
    )

    # review
    subparsers.add_parser("review", help="Lista mapeamentos com NEEDS REVIEW")

    # stats
    subparsers.add_parser("stats", help="Distribuição de heurísticas e cobertura")

    # test
    subparsers.add_parser("test", help="Executa pytest")

    return parser


def main() -> None:
    """Entrypoint principal."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "review":
        cmd_review(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
