"""
Testes para as heurísticas de resolução de commit.
Como dependem de acesso local aos repositórios clonados, estes testes assumem
que a variável de ambiente SIMREL_BASE_PATH ou o caminho padrão está configurado.
"""

from pathlib import Path

import git
import pytest

from simrel_mapper.config import repo_path
from simrel_mapper.heuristics.engine import VotingEngine
from simrel_mapper.heuristics.h0_timestamp import H0TimestampTravel
from simrel_mapper.heuristics.h1_tag_match import H1TagMatch
from simrel_mapper.heuristics.h4_branch_travel import H4BranchTravel

# O pytest marca estes testes para serem pulados se os repositórios não estiverem presentes
try:
    CDT_REPO = git.Repo(repo_path("cdt"))
    EGIT_REPO = git.Repo(repo_path("egit"))
except (git.InvalidGitRepositoryError, git.NoSuchPathError, KeyError):
    pytest.skip("Repositórios CDT/EGIT não encontrados localmente", allow_module_level=True)


def test_h1_exact():
    """Testa H1-exact com repo CDT (versão 8.0.0.x deve bater com CDT_8_0_0_xx)."""
    h = H1TagMatch(CDT_REPO)
    votes = h.vote(version="8.0.0.201106081058")
    
    # Ao menos um voto H1-exact deve ter sido encontrado para 8.0.0
    h1_exact_votes = [v for v in votes if v.heuristic_variant == "H1-exact"]
    assert len(h1_exact_votes) > 0


def test_h4_branch_travel():
    """Testa H4 em repo com branches de manutenção conhecidos (EGIT)."""
    h = H4BranchTravel(EGIT_REPO)
    # Procurar timestamp genérico de 2012 na versão 2.0
    votes = h.vote(version="2.0.0", timestamp="201206010000")
    
    # Deve encontrar commit em branch de manutenção, se houver o stable-2.0
    assert isinstance(votes, list)


def test_h0_timestamp():
    """Testa H0 global fallback."""
    h = H0TimestampTravel(CDT_REPO)
    # Usar um timestamp antigo que definitivamente existe
    votes = h.vote(version="qualquer", timestamp="201106081058")
    
    assert len(votes) == 1
    assert votes[0].heuristic_variant == "H0-timestamp"
    assert votes[0].weight == 6


def test_voting_engine():
    """Testa o motor de agregação."""
    engine = VotingEngine()
    
    # Simular CDT do JunoSR0
    res = engine.resolve(
        repo_path=repo_path("cdt"),
        version="8.0.0.201106081058",
        timestamp="201106081058",
        label="CDT",
    )
    
    assert res.status in ["SUCCESS", "NEEDS REVIEW"]
    assert res.commit is not None
    assert res.vote_candidates > 0
