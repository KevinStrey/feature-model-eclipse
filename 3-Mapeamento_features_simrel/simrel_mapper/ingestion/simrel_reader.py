"""
Leitor do repositório simrel.build via gitpython.

Itera releases (tags) do simrel.build e fornece acesso aos arquivos
.aggrcon/.b3aggrcon de cada release sem realizar checkout — todo acesso
é feito via tree/blob do gitpython.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import git

from models import ReleaseRef


def _resolve_tag_commit(tag: git.TagReference) -> git.Commit:
    """Resolve uma tag (lightweight ou anotada) para seu commit."""
    obj = tag.tag if tag.tag else tag.commit
    # Tags anotadas: tag.tag é um TagObject cujo .object aponta para o commit
    while hasattr(obj, "object"):
        obj = obj.object
    return obj


def iter_releases(simrel_repo_path: Path) -> Iterator[ReleaseRef]:
    """Itera todas as releases do simrel.build em ordem cronológica.

    Cada release é identificada por uma tag git. Retorna ReleaseRef com
    acesso à tree para leitura dos arquivos sem checkout.

    Args:
        simrel_repo_path: caminho local do repositório simrel.build.

    Yields:
        ReleaseRef para cada tag, ordenado por data de commit.
    """
    repo = git.Repo(str(simrel_repo_path))
    tags = sorted(repo.tags, key=lambda t: _resolve_tag_commit(t).committed_date)

    for tag in tags:
        commit = _resolve_tag_commit(tag)
        yield ReleaseRef(
            name=tag.name,
            commit_sha=commit.hexsha,
            tree=commit.tree,
        )


def get_release_by_name(
    simrel_repo_path: Path,
    name: str,
) -> ReleaseRef | None:
    """Encontra uma release específica pelo nome da tag.

    Args:
        simrel_repo_path: caminho local do repositório simrel.build.
        name: nome da tag a buscar.

    Returns:
        ReleaseRef ou None se não encontrada.
    """
    repo = git.Repo(str(simrel_repo_path))
    for tag in repo.tags:
        if tag.name == name:
            commit = _resolve_tag_commit(tag)
            return ReleaseRef(
                name=tag.name,
                commit_sha=commit.hexsha,
                tree=commit.tree,
            )
    return None


def get_releases_in_range(
    simrel_repo_path: Path,
    from_name: str | None = None,
    to_name: str | None = None,
) -> list[ReleaseRef]:
    """Retorna releases em um intervalo de nomes (ordem cronológica).

    Args:
        simrel_repo_path: caminho local do repositório simrel.build.
        from_name: nome da tag inicial (inclusive). None = desde o início.
        to_name: nome da tag final (inclusive). None = até o fim.

    Returns:
        Lista de ReleaseRef no intervalo.
    """
    all_releases = list(iter_releases(simrel_repo_path))

    start_idx = 0
    end_idx = len(all_releases)

    if from_name:
        for i, r in enumerate(all_releases):
            if r.name == from_name:
                start_idx = i
                break

    if to_name:
        for i, r in enumerate(all_releases):
            if r.name == to_name:
                end_idx = i + 1
                break

    return all_releases[start_idx:end_idx]


def iter_aggrcon_blobs(
    tree: git.Tree,
) -> Iterator[tuple[str, str]]:
    """Itera os arquivos .aggrcon/.b3aggrcon de uma tree git.

    Acessa o conteúdo via blob.data_stream sem fazer checkout.

    Args:
        tree: objeto Tree do gitpython (de um commit/tag).

    Yields:
        Tuplas (filename, xml_content) para cada arquivo encontrado.
    """
    for blob in tree.traverse():
        if hasattr(blob, "name") and blob.name.endswith((".aggrcon", ".b3aggrcon")):
            try:
                content = blob.data_stream.read().decode("utf-8")
                yield blob.name, content
            except Exception:
                # Arquivos binários ou corrompidos — pular silenciosamente
                continue
