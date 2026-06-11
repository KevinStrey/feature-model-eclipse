"""
Testes para o parser XML de arquivos .aggrcon/.b3aggrcon.
"""

from pathlib import Path

from simrel_mapper.ingestion.aggrcon_parser import parse_aggrcon

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_a1_cdt():
    """Testa a extração A1 com o fixture cdt.b3aggrcon (JunoSR0)."""
    xml_content = (FIXTURES_DIR / "cdt.b3aggrcon").read_text(encoding="utf-8")
    results = parse_aggrcon(xml_content, "cdt.b3aggrcon")
    
    assert len(results) == 1
    ext = results[0]
    
    assert ext.label == "CDT"
    assert ext.version == "8.0.0.201106081058"
    assert ext.timestamp == "201106081058"
    assert ext.extraction_heuristic == "A1"
    assert ext.extraction_weight == 10
    assert "org.eclipse.cdt.feature.group" in ext.features


def test_parse_a2_emf():
    """Testa a extração A2 com o fixture emf-emf.aggrcon (2026-03)."""
    xml_content = (FIXTURES_DIR / "emf-emf.aggrcon").read_text(encoding="utf-8")
    results = parse_aggrcon(xml_content, "emf-emf.aggrcon")
    
    assert len(results) == 1
    ext = results[0]
    
    assert ext.label == "EMF (Core)"
    assert ext.version == "2.45.0"
    assert ext.timestamp is None
    assert ext.extraction_heuristic == "A2"
    assert ext.extraction_weight == 6
    assert "org.eclipse.emf.sdk.feature.group" in ext.features


def test_parse_a3_ep():
    """Testa a extração A3 com o fixture ep.aggrcon (2026-03)."""
    xml_content = (FIXTURES_DIR / "ep.aggrcon").read_text(encoding="utf-8")
    results = parse_aggrcon(xml_content, "ep.aggrcon")
    
    assert len(results) == 1
    ext = results[0]
    
    assert ext.label == "Eclipse"
    assert ext.version == "4.39"
    assert ext.timestamp == "202602260420"
    assert ext.extraction_heuristic == "A3"
    assert ext.extraction_weight == 9
    assert "org.eclipse.sdk.feature.group" in ext.features
