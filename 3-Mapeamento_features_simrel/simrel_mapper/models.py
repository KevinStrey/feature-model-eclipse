"""
Modelos Pydantic para o pipeline simrel_mapper.

Todos os dados intermediários e de saída são representados por estes modelos,
garantindo validação de tipos e serialização JSON determinística.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ingestion
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


# ---------------------------------------------------------------------------
# Resultado Final
# ---------------------------------------------------------------------------

class MappingResult(BaseModel):
    """Resultado do mapeamento de uma feature para um commit."""

    version: str | None = Field(None, description="Tag do git encontrada")
    status: str = Field(..., description="SUCCESS | NOT FOUND")
    commit: str | None = Field(None, description="SHA do commit mapeado")
    repository: str | None = Field(None, description="Nome da pasta do repo local")


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
