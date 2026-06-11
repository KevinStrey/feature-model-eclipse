"""
H1 — Tag Match: resolve commit pela correspondência entre tags do repositório
e a versão extraída da feature.

Variantes (em ordem de prioridade):
  H1-exact       (peso 10) — dígitos de versão batem exatamente
  H1-date-suffix (peso  9) — tag termina com -YYYYMMDD e versão bate
  H1-date-prefix (peso  9) — tag começa com data e contém versão
  H1-loose       (peso  7) — tag contém dígitos + "release"
  H1-partial     (peso  6) — tag contém apenas major.minor
"""

from __future__ import annotations

import difflib
import re
from datetime import datetime

import git

from heuristics.base import (
    Heuristic,
    HeuristicVote,
    digits_of,
    resolve_tag_commit,
    version_digits,
)

# Regex para detectar sufixo de data -YYYYMMDD
_DATE_SUFFIX = re.compile(r"-(\d{8})$")

# Regex para detectar prefixo de data YYYY-MM-DD ou YYYYMMDD
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{8})[_\-]")

# Regex para extrair qualificador de data que começa com v e tem pelo menos 8 dígitos (ex: v20120611)
_QUALIFIER_PREFIX = re.compile(r"\.(v\d{8,}(?:[_\-\.]\d{4})?)")


class H1TagMatch(Heuristic):
    """Heurística H1: encontra commits via correspondência de tags."""

    def vote(
        self,
        version: str,
        timestamp: str | None = None,
        simrel_date: datetime | None = None,
    ) -> list[HeuristicVote]:
        """Vota em commits cujas tags correspondem à versão.

        Itera todas as tags do repositório e aplica as 5 variantes.
        Retorna todos os votos encontrados (pode haver vários).
        """
        v_digits_3 = version_digits(version, 3)
        v_digits_2 = version_digits(version, 2)
        all_digits = digits_of(version)

        if not v_digits_3:
            return []

        qualifier_match = _QUALIFIER_PREFIX.search(version)
        qualifier_str = qualifier_match.group(1) if qualifier_match else None

        votes: list[HeuristicVote] = []

        # --- Busca por Similaridade (H1-similarity) ---
        similarity_targets = [f"v{version}"]
        if qualifier_str:
            similarity_targets.append(qualifier_str)
            
        v_major_minor_micro = ".".join(v_digits_3) if len(v_digits_3) == 3 else None
        if v_major_minor_micro:
            similarity_targets.append(v_major_minor_micro)

        best_sim_ratio = 0.0
        best_sim_tags = []

        for tag in self.repo.tags:
            tag_name = tag.name
            # Calcular a maior similaridade desta tag contra os alvos (ex: 'v20120611')
            max_tag_ratio = 0.0
            for target in similarity_targets:
                ratio = difflib.SequenceMatcher(None, tag_name, target).ratio()
                if ratio > max_tag_ratio:
                    max_tag_ratio = ratio
                    
            if max_tag_ratio > best_sim_ratio:
                best_sim_ratio = max_tag_ratio
                best_sim_tags = [(tag, tag_name)]
            elif max_tag_ratio == best_sim_ratio:
                best_sim_tags.append((tag, tag_name))

        # Se a similaridade for muito alta (>= 80%), prioriza ela e retorna, ignorando lógica binária
        if best_sim_ratio >= 0.8:
            # Trava para proteger contra falsos positivos em strings curtas (ex: '1.2.0' vs 'V1.12.0')
            best_target_len = max((len(t) for t in similarity_targets), default=0)
            if best_target_len < 8 and best_sim_ratio < 0.95:
                pass # Descarta matches que não sejam praticamente exatos para targets curtos
            else:
                weight = int(best_sim_ratio * 100)
                for b_tag, b_name in best_sim_tags:
                    votes.append(self._make_vote(b_tag, b_name, f"H1-sim({best_sim_ratio*100:.1f}%)", weight))
                return votes

        # Caso as heurísticas de nome (similaridade) não atinjam um limiar satisfatório, 
        # processa as heurísticas originais binárias
        for tag in self.repo.tags:
            tag_name = tag.name
            t_digits = digits_of(tag_name)

            # --- H1-exact (peso 10) ---
            if self._match_exact(v_digits_3, t_digits):
                votes.append(self._make_vote(tag, tag_name, "H1-exact", 10))
                continue

            # --- H1-date-suffix (peso 9) ---
            if self._match_date_suffix(tag_name, v_digits_3, t_digits):
                votes.append(self._make_vote(tag, tag_name, "H1-date-suffix", 9))
                continue

            # --- H1-date-prefix (peso 9) ---
            if self._match_date_prefix(tag_name, version):
                votes.append(self._make_vote(tag, tag_name, "H1-date-prefix", 9))
                continue

            # --- H1-loose (peso 7) ---
            if self._match_loose(tag_name, v_digits_3):
                votes.append(self._make_vote(tag, tag_name, "H1-loose", 7))
                continue



        return votes

    # ------------------------------------------------------------------
    # Variantes de match
    # ------------------------------------------------------------------

    @staticmethod
    def _match_exact(v_digits_3: list[str], t_digits: list[str]) -> bool:
        """H1-exact: os 3 primeiros dígitos da versão são subsequência dos dígitos da tag."""
        if len(v_digits_3) < 3 or len(t_digits) < 3:
            return False
        # Verificar se v_digits_3 aparece como subsequência contígua em t_digits
        for i in range(len(t_digits) - len(v_digits_3) + 1):
            if t_digits[i : i + len(v_digits_3)] == v_digits_3:
                return True
        return False

    @staticmethod
    def _match_date_suffix(
        tag_name: str,
        v_digits_3: list[str],
        t_digits: list[str],
    ) -> bool:
        """H1-date-suffix: tag termina com -YYYYMMDD e a parte de versão bate."""
        m = _DATE_SUFFIX.search(tag_name)
        if not m:
            return False
        # Remover o sufixo de data e verificar os dígitos restantes
        prefix = tag_name[: m.start()]
        prefix_digits = digits_of(prefix)
        if len(prefix_digits) < 3:
            return False
        for i in range(len(prefix_digits) - len(v_digits_3) + 1):
            if prefix_digits[i : i + len(v_digits_3)] == v_digits_3:
                return True
        return False

    @staticmethod
    def _match_date_prefix(tag_name: str, version: str) -> bool:
        """H1-date-prefix: tag começa com data e contém a versão como sufixo."""
        m = _DATE_PREFIX.match(tag_name)
        if not m:
            return False
        # Parte após a data
        suffix = tag_name[m.end():]
        # Verificar se os dígitos da versão estão no sufixo
        v_digits = version_digits(version, 3)
        s_digits = digits_of(suffix)
        if len(s_digits) < 3:
            return False
        for i in range(len(s_digits) - len(v_digits) + 1):
            if s_digits[i : i + len(v_digits)] == v_digits:
                return True
        return False

    @staticmethod
    def _match_loose(tag_name: str, v_digits_3: list[str]) -> bool:
        """H1-loose: tag contém dígitos da versão E a palavra 'release'."""
        if "release" not in tag_name.lower():
            return False
        t_digits = digits_of(tag_name)
        if len(t_digits) < 3:
            return False
        for i in range(len(t_digits) - len(v_digits_3) + 1):
            if t_digits[i : i + len(v_digits_3)] == v_digits_3:
                return True
        return False



    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _make_vote(
        self,
        tag: git.TagReference,
        tag_name: str,
        variant: str,
        weight: int,
    ) -> HeuristicVote:
        """Cria um HeuristicVote a partir de uma tag."""
        commit = resolve_tag_commit(tag)
        return HeuristicVote(
            commit_sha=commit.hexsha,
            heuristic_id="H1",
            heuristic_variant=variant,
            weight=weight,
            matched_value=tag_name,
        )
