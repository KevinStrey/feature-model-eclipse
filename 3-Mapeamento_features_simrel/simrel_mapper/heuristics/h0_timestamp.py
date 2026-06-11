"""
H0 — Timestamp Time-Travel (peso=6).

Fallback mais amplo: encontra o commit mais recente em qualquer branch
antes do timestamp de build.

Requer timestamp disponível (A1 ou A3).
"""

from __future__ import annotations

from __future__ import annotations

import datetime
from datetime import timezone

import git

from heuristics.base import Heuristic, HeuristicVote


def _parse_timestamp(ts: str) -> datetime.datetime:
    """Converte um timestamp de 12 dígitos para datetime UTC."""
    return datetime.datetime.strptime(ts[:12], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)


class H0TimestampTravel(Heuristic):
    """Heurística H0: commit mais recente antes do timestamp em qualquer branch."""

    def vote(
        self,
        version: str,
        timestamp: str | None = None,
        simrel_date: datetime.datetime | None = None,
    ) -> list[HeuristicVote]:
        """Vota no commit mais recente global antes do timestamp.

        Requer timestamp. Retorna lista vazia se indisponível.
        Sempre executado como fallback quando timestamp presente.
        """
        if not timestamp:
            return []

        dt = _parse_timestamp(timestamp)

        try:
            commits = list(
                self.repo.iter_commits(
                    all=True,
                    until=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    max_count=1,
                )
            )
            if commits:
                return [HeuristicVote(
                    commit_sha=commits[0].hexsha,
                    heuristic_id="H0",
                    heuristic_variant="H0-timestamp",
                    weight=6,
                    matched_value=f"timestamp={timestamp}",
                )]
        except (git.GitCommandError, StopIteration):
            pass

        return []
