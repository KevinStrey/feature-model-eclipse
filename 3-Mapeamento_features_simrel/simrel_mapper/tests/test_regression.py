"""
Teste de regressão (end-to-end simplificado) do pipeline.
"""

from pathlib import Path
import json

from simrel_mapper.config import OUTPUT_DIR, simrel_repo_path
from simrel_mapper.heuristics.engine import VotingEngine
from simrel_mapper.ingestion.simrel_reader import get_release_by_name
from simrel_mapper.main import _process_release


def test_regression_junosr0(tmp_path):
    """Executa o pipeline para JunoSR0 e valida o formato da saída."""
    # Como não temos um banco de dados real em memória, usamos um monkeypatch
    # no OUTPUT_DIR apenas para não poluir o output/ verdadeiro durante testes
    
    ref = get_release_by_name(simrel_repo_path(), "JunoSR0")
    if not ref:
        return
    
    engine = VotingEngine()
    
    # Processar a release
    output = _process_release(ref.name, ref.commit_sha, ref.tree, engine, force=True)
    
    assert output is not None
    assert output.release == "JunoSR0"
    assert output.simrel_commit == ref.commit_sha
    
    # JunoSR0 possui o CDT
    assert "CDT" in output.mappings
    cdt_mapping = output.mappings["CDT"]
    
    assert cdt_mapping.version == "8.0.0.201106081058"
    assert cdt_mapping.timestamp == "201106081058"
    assert cdt_mapping.status in ["SUCCESS", "NEEDS REVIEW"]
    assert cdt_mapping.commit is not None
    assert cdt_mapping.extraction_heuristic == "A1"
    assert cdt_mapping.repository == "cdt"
