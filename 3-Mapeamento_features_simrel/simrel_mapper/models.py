"""
Modelos Pydantic para o pipeline simrel_mapper.

Todos os dados intermediários e de saída são representados por estes modelos,
garantindo validação de tipos e serialização JSON determinística.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingestion (Parte 1)
# ---------------------------------------------------------------------------

class ReleaseRef(BaseModel):
    """Referência a uma release do simrel.build (tag git)."""

    name: str = Field(..., description="Nome da tag, ex: 'JunoSR0', '2024-03'")
    commit_sha: str = Field(..., description="SHA do commit associado à tag")
    tree: Any = Field(
        ...,
        exclude=True,
        description="Objeto gitpython Tree — excluído da serialização",
    )

    model_config = {"arbitrary_types_allowed": True}


class ExtractionResult(BaseModel):
    """Resultado da extração de um arquivo .aggrcon / .b3aggrcon."""

    label: str = Field(..., description="Label da contribuição, ex: 'CDT'")
    version: str | None = Field(None, description="Versão extraída")
    timestamp: str | None = Field(None, description="Timestamp de build (12 dígitos)")
    p2_url: str | None = Field(None, description="URL do repositório p2")
    extraction_heuristic: str = Field(
        ..., description="Heurística usada: 'A1', 'A2', 'A3' ou 'PARSE_ERROR'"
    )
    extraction_weight: int = Field(0, description="Peso da heurística de extração")
    filename: str = Field(..., description="Nome do arquivo de origem")
    features: list[str] = Field(
        default_factory=list,
        description="Nomes das features encontradas neste repositório",
    )


# ---------------------------------------------------------------------------
# Heurísticas (Parte 2)
# ---------------------------------------------------------------------------

class HeuristicVote(BaseModel):
    """Voto de uma heurística de resolução de commit."""

    commit_sha: str = Field(..., description="SHA do commit candidato")
    heuristic_id: str = Field(..., description="ID da heurística: 'H0', 'H1', 'H4'")
    heuristic_variant: str = Field(
        ..., description="Variante específica, ex: 'H1-exact', 'H4-branch'"
    )
    weight: int = Field(..., description="Peso do voto")
    matched_value: str = Field(
        ..., description="Valor que gerou o match: nome da tag, branch, etc."
    )


# ---------------------------------------------------------------------------
# Resultado Final
# ---------------------------------------------------------------------------

class MappingResult(BaseModel):
    """Resultado do mapeamento de uma feature para um commit."""

    version: str | None = Field(None)
    timestamp: str | None = Field(None)
    status: str = Field(..., description="SUCCESS | NEEDS REVIEW | NOT FOUND")
    commit: str | None = Field(None, description="SHA do commit vencedor")
    extraction_heuristic: str | None = Field(None, description="A1, A2 ou A3")
    heuristic_id: str | None = Field(None, description="H0, H1 ou H4")
    heuristic_description: str | None = Field(
        None, description="Descrição legível das heurísticas vencedoras"
    )
    matched_value: str | None = Field(None)
    repository: str | None = Field(None, description="Nome da pasta do repo local")
    vote_total_weight: int = Field(0)
    vote_candidates: int = Field(0)


class ReleaseOutput(BaseModel):
    """Saída completa de uma release — serializada para JSON."""

    release: str = Field(..., description="Nome da release (tag)")
    simrel_commit: str = Field(
        ..., description="SHA do commit do simrel.build para reprodutibilidade"
    )
    mappings: dict[str, MappingResult] = Field(
        default_factory=dict,
        description="label → MappingResult",
    )
