"""
H4 — Maintenance Branch Time-Travel (peso=8).

Encontra o commit mais recente antes do timestamp em branches de manutenção
cujo padrão de versão corresponde à versão da feature.

Requer timestamp disponível (A1 ou A3).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import git

from heuristics.base import Heuristic, HeuristicVote, version_digits

# Padrões de nomes de branches de manutenção
MAINTENANCE_PATTERNS: list[re.Pattern] = [
    re.compile(r"stable-(\d+)\.(\d+)"),
    re.compile(r"R(\d+)_(\d+)_maintenance"),
    re.compile(r"maintenance/(\d+)\.(\d+)"),
    re.compile(r"releases/(\d+)\.(\d+)"),
    re.compile(r"(\d+)\.(\d+)\.x"),
]


def _parse_timestamp(ts: str) -> datetime:
    """Converte um timestamp de 12 dígitos para datetime UTC.

    Formato: YYYYMMDDHHmm → datetime.
    """
    return datetime.strptime(ts[:12], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)


def _branch_version_matches(
    branch_name: str,
    major: str,
    minor: str,
) -> bool:
    """Verifica se o nome do branch de manutenção contém a versão major.minor.

    Testa todos os padrões de MAINTENANCE_PATTERNS.
    """
    for pattern in MAINTENANCE_PATTERNS:
        m = pattern.search(branch_name)
        if m and m.group(1) == major and m.group(2) == minor:
            return True
    return False


class H4BranchTravel(Heuristic):
    """Heurística H4: commit mais recente antes do timestamp em branch de manutenção."""

    def vote(
        self,
        version: str,
        timestamp: str | None = None,
    ) -> list[HeuristicVote]:
        """Vota no commit mais recente antes do timestamp em branches de manutenção.

        Requer timestamp. Retorna lista vazia se timestamp indisponível.
        """
        if not timestamp:
            return []

        v_digits = version_digits(version, 2)
        if len(v_digits) < 2:
            return []

        major, minor = v_digits[0], v_digits[1]
        dt = _parse_timestamp(timestamp)

        votes: list[HeuristicVote] = []

        try:
            remote_refs = self.repo.remote("origin").refs
        except (ValueError, git.GitCommandError):
            return []

        for ref in remote_refs:
            branch_name = ref.name
            if not _branch_version_matches(branch_name, major, minor):
                continue

            try:
                # Commit mais recente antes do timestamp neste branch
                commits = list(
                    self.repo.iter_commits(
                        ref,
                        until=dt.strftime("%Y-%m-%d %H:%M:%S"),
                        max_count=1,
                    )
                )
                if commits:
                    votes.append(HeuristicVote(
                        commit_sha=commits[0].hexsha,
                        heuristic_id="H4",
                        heuristic_variant="H4-branch",
                        weight=8,
                        matched_value=branch_name,
                    ))
            except (git.GitCommandError, StopIteration):
                continue

        return votes
