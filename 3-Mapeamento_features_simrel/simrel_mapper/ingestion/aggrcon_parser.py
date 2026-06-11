"""
Parser de arquivos .aggrcon e .b3aggrcon do simrel.build.

Aplica as heurísticas de extração A1, A2 e A3 para obter
(label, version, timestamp, p2_url) de cada contribuição.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from models import ExtractionResult

# ---------------------------------------------------------------------------
# Namespaces conhecidos
# ---------------------------------------------------------------------------

NAMESPACE_B3 = "http://www.eclipse.org/b3/2011/aggregator/1.1.0"
NAMESPACE_CBI = "http://www.eclipse.org/cbi/p2repo/2011/aggregator/1.1.0"

# Prefixos usados pelo ElementTree ao parsear namespaces
_NS_PREFIXES = {
    NAMESPACE_B3: f"{{{NAMESPACE_B3}}}",
    NAMESPACE_CBI: f"{{{NAMESPACE_CBI}}}",
}

# ---------------------------------------------------------------------------
# Regex para extração de versão
# ---------------------------------------------------------------------------

# A3: R-4.40-202606010713  ou  S-3.8.0M4-201206010713
_PATTERN_A3 = re.compile(r"[RS]-([\d]+\.[\d]+(?:\.[\d]+)?(?:\.[^\-]*)?)-(\d{12})")

# A2: último segmento de versão semântica na URL
_PATTERN_SEMVER = re.compile(r"(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)")

# Timestamp embutido na versão A1: qualifier com data (8) e hora (4) opcionalmente separados
_PATTERN_QUALIFIER_TS = re.compile(r"v?(\d{8})[_\-\.]?(\d{4})")


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------


def _detect_namespace(root: ET.Element) -> str | None:
    """Detecta o namespace do elemento raiz.

    Retorna NAMESPACE_B3, NAMESPACE_CBI ou None.
    """
    tag = root.tag
    for ns, prefix in _NS_PREFIXES.items():
        if tag.startswith(prefix):
            return ns
    # Fallback: procurar no atributo xmlns:aggregator
    for attr_name, attr_val in root.attrib.items():
        if "aggregator" in attr_name.lower() and "b3" in attr_val:
            return NAMESPACE_B3
        if "aggregator" in attr_name.lower() and "cbi" in attr_val:
            return NAMESPACE_CBI
    return None


def _has_feature_version_range(root: ET.Element) -> bool:
    """Verifica se algum <features> possui atributo versionRange com versão exata.

    Ignora ranges de dependência como '[1.0.0,2.0.0)' — esses contêm colchetes.
    Foca apenas em <features>, não em <bundles>.
    """
    for elem in root.iter():
        local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local_name != "features":
            continue
        vr = elem.get("versionRange", "")
        if vr and "," not in vr:
            return True
    return False


def _get_label(root: ET.Element) -> str:
    """Extrai o label da tag raiz <aggregator:Contribution>."""
    return root.get("label", "UNKNOWN")


def _iter_repositories(root: ET.Element) -> list[ET.Element]:
    """Retorna todos os elementos <repositories> do documento."""
    repos: list[ET.Element] = []
    for elem in root.iter():
        local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local_name == "repositories":
            repos.append(elem)
    return repos


def _get_features(repo_elem: ET.Element) -> list[ET.Element]:
    """Retorna elementos <features> filhos de um <repositories>."""
    features: list[ET.Element] = []
    for child in repo_elem:
        local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local_name == "features":
            features.append(child)
    return features


def _pick_main_feature_version(features: list[ET.Element]) -> tuple[str | None, list[str]]:
    """Dentre features com versionRange, retorna a versão da feature principal.

    A feature principal é a de nome mais curto (mais genérica).
    Também retorna a lista de nomes de features.
    """
    candidates: list[tuple[str, str]] = []
    all_names: list[str] = []
    for f in features:
        name = f.get("name", "")
        all_names.append(name)
        vr = f.get("versionRange", "")
        # Ignorar ranges de dependência que possuem vírgula
        if vr and "," not in vr:
            if vr.startswith("[") and vr.endswith("]"):
                vr = vr[1:-1]
            candidates.append((name, vr))

    if not candidates:
        return None, all_names

    # Feature principal = nome mais curto
    candidates.sort(key=lambda x: len(x[0]))
    return candidates[0][1], all_names


def _extract_timestamp_from_version(version: str) -> str | None:
    """Extrai timestamp (qualifier) de uma versão OSGi.

    '8.0.0.201106081058' → '201106081058'
    '8.0.0' → None
    """
    parts = version.split(".")
    if len(parts) >= 4:
        qualifier = parts[3]
        m = _PATTERN_QUALIFIER_TS.search(qualifier)
        if m:
            return m.group(1) + m.group(2)
    return None


# ---------------------------------------------------------------------------
# Heurísticas de Extração
# ---------------------------------------------------------------------------


def _extract_a1(
    root: ET.Element,
    filename: str,
) -> list[ExtractionResult]:
    """A1 — versionRange explícito (peso=10, formato .b3aggrcon)."""
    label = _get_label(root)
    results: list[ExtractionResult] = []

    for repo_elem in _iter_repositories(root):
        p2_url = repo_elem.get("location", "")
        features = _get_features(repo_elem)
        version, feature_names = _pick_main_feature_version(features)

        if version is None:
            # Se não há features com versionRange, tentar bundles como fallback
            # (mas priorizando features conforme requisito)
            continue

        timestamp = _extract_timestamp_from_version(version)

        results.append(ExtractionResult(
            label=label,
            version=version,
            timestamp=timestamp,
            p2_url=p2_url,
            extraction_heuristic="A1",
            extraction_weight=10,
            filename=filename,
            features=feature_names,
        ))

    return results


def _extract_a2_or_a3(
    root: ET.Element,
    filename: str,
) -> list[ExtractionResult]:
    """A2/A3 — versão na URL (formato .aggrcon novo)."""
    label = _get_label(root)
    results: list[ExtractionResult] = []

    for repo_elem in _iter_repositories(root):
        p2_url = repo_elem.get("location", "")
        features = _get_features(repo_elem)
        feature_names = [f.get("name", "") for f in features]

        # Tentar A3 primeiro (versão + timestamp na URL)
        m_a3 = _PATTERN_A3.search(p2_url)
        if m_a3:
            results.append(ExtractionResult(
                label=label,
                version=m_a3.group(1),
                timestamp=m_a3.group(2),
                p2_url=p2_url,
                extraction_heuristic="A3",
                extraction_weight=9,
                filename=filename,
                features=feature_names,
            ))
            continue

        # A2 — versão semântica na URL
        # Pegar o último match de semver no path da URL
        all_semver = _PATTERN_SEMVER.findall(p2_url)
        if all_semver:
            version = all_semver[-1]  # último segmento
            results.append(ExtractionResult(
                label=label,
                version=version,
                timestamp=None,
                p2_url=p2_url,
                extraction_heuristic="A2",
                extraction_weight=6,
                filename=filename,
                features=feature_names,
            ))
            continue

        # Nenhuma versão encontrada na URL
        results.append(ExtractionResult(
            label=label,
            version=None,
            timestamp=None,
            p2_url=p2_url,
            extraction_heuristic="A2",
            extraction_weight=0,
            filename=filename,
            features=feature_names,
        ))

    return results


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def parse_aggrcon(xml_content: str, filename: str) -> list[ExtractionResult]:
    """Parseia um arquivo .aggrcon ou .b3aggrcon e retorna os resultados de extração.

    Detecta o namespace e aplica A1, A2 ou A3 conforme o formato.
    Nunca lança exceção — erros retornam ExtractionResult com
    extraction_heuristic='PARSE_ERROR'.

    Args:
        xml_content: conteúdo XML do arquivo.
        filename: nome do arquivo para rastreabilidade.

    Returns:
        Lista de ExtractionResult (pode ser >1 se houver múltiplos <repositories>).
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return [ExtractionResult(
            label="PARSE_ERROR",
            version=None,
            timestamp=None,
            p2_url=None,
            extraction_heuristic="PARSE_ERROR",
            extraction_weight=0,
            filename=filename,
            features=[],
        )]

    namespace = _detect_namespace(root)

    # Se namespace b3 OU qualquer <features> tem versionRange exato → A1
    if namespace == NAMESPACE_B3 or _has_feature_version_range(root):
        results = _extract_a1(root, filename)
        if results:
            return results
        # Fallback: se A1 não encontrou nada, tentar A2/A3
        return _extract_a2_or_a3(root, filename)

    # Caso contrário → A2 ou A3 baseado na URL
    return _extract_a2_or_a3(root, filename)
