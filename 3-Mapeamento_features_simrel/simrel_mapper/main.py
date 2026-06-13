"""
CLI principal do pipeline simrel_mapper.

Subcomandos:
    run      — processa releases do simrel.build
    stats    — distribuição de status
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
from config import OUTPUT_DIR, DISPLAY_NAMES, repo_path, simrel_repo_path
from ingestion.simrel_reader import (
    get_release_by_name,
    get_releases_in_range,
    iter_releases,
)
from models import MappingResult, ReleaseOutput

console = Console()


def get_git_tag(repo_obj: git.Repo, commit_hash: str) -> str | None:
    """Retorna a tag pura do git usando git describe --contains."""
    try:
        raw_describe = repo_obj.git.describe("--contains", commit_hash)
        if raw_describe:
            # git describe --contains output: tag_name~X or tag_name^Y
            tag_clean = raw_describe.split("~")[0].split("^")[0]
            return tag_clean.strip()
    except Exception:
        pass
    return None


def _process_release(
    release_name: str,
    simrel_commit: str,
    force: bool,
) -> ReleaseOutput | None:
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
        log.error("simrel_date_error", error=str(e), commit=simrel_commit)
        return None

    mappings: dict[str, MappingResult] = {}

    from config import BASE_PATH
    for folder_name, display_name in DISPLAY_NAMES.items():
        local_repo = BASE_PATH / folder_name

        if not local_repo.exists():
            log.warning("repo_missing", repo=folder_name, path=str(local_repo))
            mappings[display_name] = MappingResult(
                status="NOT FOUND",
                repository=folder_name,
            )
            continue

        try:
            repo_obj = git.Repo(str(local_repo))
            commit_hash = repo_obj.git.log(
                all=True,
                format="%H",
                max_count=1,
                date_order=True,
                until=int(simrel_date.timestamp()),
            )

            if commit_hash:
                commit_hash = commit_hash.strip()
                tag = get_git_tag(repo_obj, commit_hash)
                mappings[display_name] = MappingResult(
                    version=tag,
                    status="SUCCESS",
                    commit=commit_hash,
                    repository=folder_name,
                )
            else:
                mappings[display_name] = MappingResult(
                    status="NOT FOUND",
                    repository=folder_name,
                )

        except Exception as exc:
            log.error(
                "git_log_error",
                repo=folder_name,
                error=str(exc),
            )
            mappings[display_name] = MappingResult(
                status="NOT FOUND",
                repository=folder_name,
            )

    output = ReleaseOutput(
        release=release_name,
        simrel_commit=simrel_commit,
        mappings=mappings,
    )

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
    configure_logging()
    simrel_path = simrel_repo_path()

    if args.release:
        ref = get_release_by_name(simrel_path, args.release)
        if ref is None:
            console.print(f"[red]Release '{args.release}' não encontrada.[/red]")
            sys.exit(1)
        _process_release(ref.name, ref.commit_sha, args.force)

    elif args.all:
        releases = list(iter_releases(simrel_path))
        console.print(f"[bold]Processando {len(releases)} releases...[/bold]")
        for i, ref in enumerate(releases, 1):
            console.print(f"[dim][{i}/{len(releases)}][/dim] {ref.name}", end=" ")
            result = _process_release(ref.name, ref.commit_sha, args.force)
            if result:
                success = sum(1 for m in result.mappings.values() if m.status == "SUCCESS")
                console.print(f"[green]{success}/{len(result.mappings)} SUCCESS[/green]")
            else:
                console.print("[yellow]SKIPPED[/yellow]")

    elif args.from_release or args.to_release:
        releases = get_releases_in_range(simrel_path, args.from_release, args.to_release)
        console.print(f"[bold]Processando {len(releases)} releases no intervalo...[/bold]")
        for i, ref in enumerate(releases, 1):
            console.print(f"[dim][{i}/{len(releases)}][/dim] {ref.name}", end=" ")
            result = _process_release(ref.name, ref.commit_sha, args.force)
            if result:
                success = sum(1 for m in result.mappings.values() if m.status == "SUCCESS")
                console.print(f"[green]{success}/{len(result.mappings)} SUCCESS[/green]")
            else:
                console.print("[yellow]SKIPPED[/yellow]")
    else:
        console.print("[red]Especifique --all, --release ou --from/--to.[/red]")
        sys.exit(1)


def cmd_stats(args: argparse.Namespace) -> None:
    if not OUTPUT_DIR.exists():
        console.print("[red]Diretório output/ não encontrado.[/red]")
        return

    status_counter: Counter = Counter()
    total_mappings = 0

    for json_file in sorted(OUTPUT_DIR.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for label, mapping in data.get("mappings", {}).items():
            total_mappings += 1
            status_counter[mapping.get("status", "?")] += 1

    table_status = Table(title="Distribuição — Status")
    table_status.add_column("Status")
    table_status.add_column("Count", justify="right")
    table_status.add_column("%", justify="right")
    for s, c in status_counter.most_common():
        pct = f"{c / total_mappings * 100:.1f}" if total_mappings else "0"
        table_status.add_row(s, str(c), pct)
    console.print(table_status)

    console.print(f"\n[bold]Total de mapeamentos:[/bold] {total_mappings}")
    console.print(f"[bold]Releases processadas:[/bold] {len(list(OUTPUT_DIR.glob('*.json')))}")


def cmd_test(args: argparse.Namespace) -> None:
    test_dir = Path(__file__).parent / "tests"
    subprocess.run(
        [sys.executable, "-m", "pytest", str(test_dir), "-v"],
        cwd=str(Path(__file__).parent),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simrel_mapper",
        description="Pipeline de mapeamento de releases Eclipse/simrel por tempo.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcomandos disponíveis")

    p_run = subparsers.add_parser("run", help="Processa releases")
    p_run.add_argument("--all", action="store_true")
    p_run.add_argument("--release", type=str)
    p_run.add_argument("--from", dest="from_release", type=str)
    p_run.add_argument("--to", dest="to_release", type=str)
    p_run.add_argument("--force", action="store_true")

    subparsers.add_parser("stats", help="Distribuição de cobertura")
    subparsers.add_parser("test", help="Executa pytest")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "test":
        cmd_test(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
