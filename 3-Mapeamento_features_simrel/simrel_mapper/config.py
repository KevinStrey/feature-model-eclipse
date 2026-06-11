"""
Configuração central do pipeline simrel_mapper.

BASE_PATH e demais caminhos podem ser sobrescritos via arquivo .env
na raiz do projeto.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Carrega .env se existir (nunca obrigatório)
load_dotenv()

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

BASE_PATH: Path = Path(
    os.getenv("SIMREL_BASE_PATH",
              r"C:\Users\Kevin Strey\Desktop\Feature-models\1-Repositorios")
)

OUTPUT_DIR: Path = Path(
    os.getenv("SIMREL_OUTPUT_DIR",
              str(Path(__file__).parent / "output"))
)

# ---------------------------------------------------------------------------
# Mapeamento label → pasta do repositório local
# ---------------------------------------------------------------------------

REPOSITORIES: dict[str, str] = {
    # chave = label usado no simrel, valor = nome da pasta dentro de BASE_PATH
    "simrel.build":      "simrel.build",
    "cdt":               "cdt",
    "gef-classic":       "gef-classic",
    "gef":               "gef-classic",          # mesmo repo, label diferente
    "org.eclipse.emf":   "org.eclipse.emf",
    "birt":              "birt",
    "datatools":         "datatools",
    "eclipselink":       "eclipselink",
    "egit":              "egit",
    "gmf-runtime":       "gmf-runtime",
    "org.eclipse.mylyn": "org.eclipse.mylyn",
    "org.eclipse.rap":   "org.eclipse.rap",
    "ptp":               "ptp",
    "scout.rt":          "scout.rt",
    "webtools.javaee":   "webtools.javaee",
    "windowbuilder":     "windowbuilder",
    "m2e-core":          "m2e-core",
}


def repo_path(name: str) -> Path:
    """Retorna o caminho absoluto do repositório local para o label dado.

    Raises:
        KeyError: se *name* não está em REPOSITORIES.
    """
    return BASE_PATH / REPOSITORIES[name]


def simrel_repo_path() -> Path:
    """Atalho para o caminho do repositório simrel.build."""
    return repo_path("simrel.build")
