from __future__ import annotations

import datetime

from heuristics.base import Heuristic, HeuristicVote


class H5SimrelFallback(Heuristic):
    """Heurística H5: Simrel Fallback.
    
    Usada como último recurso quando a versão extraída não possui um timestamp
    (qualificador) e nenhuma heurística de similaridade encontrou uma tag.
    
    Busca o commit mais recente no histórico do repositório que tenha ocorrido
    antes ou no mesmo momento em que o commit da release agregadora (simrel.build)
    foi congelado.
    """

    def vote(
        self,
        version: str,
        timestamp: str | None = None,
        simrel_date: datetime.datetime | None = None,
    ) -> list[HeuristicVote]:
        """Vota no último commit antes da data de congelamento da release.

        Retorna:
            Uma lista contendo o voto do commit fallback, se houver simrel_date
            disponível e se a extração padrão estiver carente de timestamp.
        """
        # Só entra em ação como fallback quando não há um timestamp na string extraída
        if timestamp is not None:
            return []

        # Precisamos da data de congelamento do repositório simrel para voltar no tempo
        if simrel_date is None:
            print(f"[DEBUG H5] simrel_date is None for {version}")
            return []

        print(f"[DEBUG H5] Running fallback for {version} with date {simrel_date}")
        try:
            # Pede pro Git trazer a hash do commit mais recente (--max-count=1)
            # de todos os branches (--all) que tenha ocorrido antes da simrel_date (--until)
            # ordenado por data (--date-order)
            commit_hash = self.repo.git.log(
                all=True,
                format="%H",
                max_count=1,
                date_order=True,
                until=int(simrel_date.timestamp()),
            )

            if commit_hash:
                # Resolve a hash string para um objeto commit real do gitpython
                commit_obj = self.repo.commit(commit_hash.strip())
                
                # Retorna o voto com peso 5 (ganha de 0, mas perde para 6, 8 e 10)
                # O matched_value carrega a data de congelamento que gerou o match
                return [
                    HeuristicVote(
                        commit_sha=commit_obj.hexsha,
                        heuristic_id="H5",
                        matched_value=f"simrel_date={simrel_date.strftime('%Y-%m-%d %H:%M:%S')}",
                        heuristic_variant="H5-simrel-fallback",
                        weight=5,
                    )
                ]
            else:
                print(f"[DEBUG H5] git log returned empty for {version}")

        except Exception as e:
            print(f"[DEBUG H5] Exception: {e}")

        return []
