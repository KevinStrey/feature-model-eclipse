"""
VotingEngine — agrega votos das heurísticas H0, H1, H4 e decide
o commit vencedor com base nos pesos acumulados.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

import git

from audit.logger import get_logger
from heuristics.base import HeuristicVote
from heuristics.h0_timestamp import H0TimestampTravel
from heuristics.h1_tag_match import H1TagMatch
from heuristics.h4_branch_travel import H4BranchTravel
from heuristics.h5_simrel_fallback import H5SimrelFallback
from models import MappingResult

# Ordem de execução das heurísticas
HEURISTIC_CLASSES = [H1TagMatch, H4BranchTravel, H0TimestampTravel, H5SimrelFallback]


class VotingEngine:
    """Motor de votação para resolução de commits.

    Executa todas as heurísticas sobre um repositório local e agrega
    os votos por commit SHA.
    """

    def resolve(
        self,
        repo_path: Path,
        version: str,
        timestamp: str | None,
        label: str,
        release_name: str = "",
        simrel_date: datetime | None = None,
    ) -> MappingResult:
        """Resolve o commit para uma feature usando votação por heurísticas.

        Args:
            repo_path: caminho do repositório local da feature.
            version: versão extraída da feature.
            timestamp: timestamp de build, se disponível.
            label: label da feature (para logging).
            release_name: nome da release (para logging).

        Returns:
            MappingResult com o commit vencedor e metadados.
        """
        log = get_logger(release=release_name, feature=label)

        try:
            repo = git.Repo(str(repo_path))
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
            log.error("repository_not_found", path=str(repo_path), error=str(exc))
            return MappingResult(
                version=version,
                timestamp=timestamp,
                status="NOT FOUND",
                repository=repo_path.name,
                commit=None,
            )

        all_votes: list[HeuristicVote] = []

        for HClass in HEURISTIC_CLASSES:
            h = HClass(repo)
            try:
                votes = h.vote(version=version, timestamp=timestamp, simrel_date=simrel_date)
                for v in votes:
                    log.info(
                        "heuristic_vote",
                        heuristic=v.heuristic_variant,
                        commit=v.commit_sha[:12],
                        weight=v.weight,
                        matched=v.matched_value,
                    )
                all_votes.extend(votes)
            except Exception as exc:
                log.warning(
                    "heuristic_error",
                    heuristic=HClass.__name__,
                    error=str(exc),
                )

        return self._aggregate(
            all_votes,
            label=label,
            version=version,
            timestamp=timestamp,
            repo_name=repo_path.name,
            log=log,
            repo=repo,
            simrel_date=simrel_date,
        )

    def _aggregate(
        self,
        votes: list[HeuristicVote],
        label: str,
        version: str,
        timestamp: str | None,
        repo_name: str,
        log,
        repo: git.Repo = None,
        simrel_date: datetime | None = None,
    ) -> MappingResult:
        """Agrega votos e determina o commit vencedor."""
        if not votes:
            log.error("no_votes", label=label, version=version)
            return MappingResult(
                version=version,
                timestamp=timestamp,
                status="NOT FOUND",
                commit=None,
                repository=repo_name,
            )

        # Agrupar por commit_sha e somar pesos
        tally: dict[str, int] = defaultdict(int)
        for v in votes:
            tally[v.commit_sha] += v.weight

        max_weight = max(tally.values())
        tied_shas = [sha for sha, w in tally.items() if w == max_weight]
        
        winner_sha = None
        tiebroken_by_date = False

        if len(tied_shas) > 1 and repo and simrel_date:
            best_diff = None
            for sha in tied_shas:
                try:
                    c = repo.commit(sha)
                    # Convert commit date to match timezone of simrel_date or treat as naive
                    # Using simple timestamp diff
                    c_date = c.committed_datetime
                    if c_date <= simrel_date:
                        diff = (simrel_date - c_date).total_seconds()
                        if best_diff is None or diff < best_diff:
                            best_diff = diff
                            winner_sha = sha
                except Exception:
                    pass
            if winner_sha:
                tiebroken_by_date = True

        if not winner_sha:
            winner_sha = tied_shas[0]

        winner_votes = [v for v in votes if v.commit_sha == winner_sha]
        vote_candidates = len(tally)
        vote_total_weight = max_weight

        # Descrição legível das heurísticas vencedoras
        desc = " + ".join(
            f"{v.heuristic_variant}({v.weight})" for v in winner_votes
        )
        if tiebroken_by_date:
            desc += " + TIEBREAKER(date)"
        heuristic_description = f"VOTE({desc})"

        # Determinar status
        if vote_total_weight < 6:
            status = "NEEDS REVIEW"
        elif len(tied_shas) > 1 and not tiebroken_by_date:
            status = "NEEDS REVIEW"
        else:
            status = "SUCCESS"

        log.info(
            "winner",
            commit=winner_sha[:12],
            total_weight=vote_total_weight,
            candidates=vote_candidates,
            status=status,
            description=heuristic_description,
        )

        if vote_candidates > 1:
            log.warning(
                "multiple_candidates",
                candidates=vote_candidates,
                weights={sha[:12]: w for sha, w in tally.items()},
            )

        return MappingResult(
            version=version,
            timestamp=timestamp,
            status=status,
            commit=winner_sha,
            heuristic_id=winner_votes[0].heuristic_id,
            heuristic_description=heuristic_description,
            matched_value=winner_votes[0].matched_value,
            repository=repo_name,
            vote_total_weight=vote_total_weight,
            vote_candidates=vote_candidates,
        )
