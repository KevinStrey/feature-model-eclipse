"""
Classe base para heurísticas de resolução de commit e funções utilitárias.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

import git

from models import HeuristicVote


class Heuristic(ABC):
    """Classe abstrata para heurísticas de resolução de commit.

    Cada heurística recebe um repositório git local e vota em um ou mais
    commits candidatos com base na versão e/ou timestamp extraídos.
    """

    def __init__(self, repo: git.Repo) -> None:
        self.repo = repo

    @abstractmethod
    def vote(
        self,
        version: str,
        timestamp: str | None = None,
    ) -> list[HeuristicVote]:
        """Retorna lista de votos (pode ser vazia se nenhum candidato encontrado).

        Args:
            version: versão extraída da feature (ex: '8.0.0.201106081058').
            timestamp: timestamp de build, se disponível (ex: '201106081058').

        Returns:
            Lista de HeuristicVote.
        """
        ...


# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------


def digits_of(version: str) -> list[str]:
    """Extrai segmentos numéricos de uma versão, separando por '.', '_', '-'.

    Exemplos:
        '8.0.0.201106081058' → ['8', '0', '0', '201106081058']
        '8.0.0' → ['8', '0', '0']
        'CDT_8_1_0' → ['8', '1', '0']
        'R2_46_0' → ['2', '46', '0']
    """
    return re.findall(r"\d+", version)


def version_digits(version: str, count: int = 3) -> list[str]:
    """Retorna os primeiros *count* dígitos de versão (major.minor.patch).

    Args:
        version: string de versão.
        count: quantos segmentos retornar.
    """
    return digits_of(version)[:count]


def resolve_tag_commit(tag: git.TagReference) -> git.Commit:
    """Resolve uma tag (lightweight ou anotada) para seu commit.

    Tags anotadas possuem um objeto intermediário TagObject;
    tags lightweight apontam diretamente para o commit.
    """
    obj = tag.tag if tag.tag else tag.commit
    while hasattr(obj, "object"):
        obj = obj.object
    return obj
