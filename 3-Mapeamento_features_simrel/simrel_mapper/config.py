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
    "jdt":               "eclipse.jdt.core",
    "pde":               "eclipse.pde",
    "cdt":               "cdt",
    "gef-classic":       "gef-classic",
    "gef":               "gef-classic",          # mesmo repo, label diferente
    "org.eclipse.emf":   "org.eclipse.emf",
    "birt":              "birt",
    "datatools":         "datatools",
    "eclipselink":       "eclipselink",
    "egit":              "egit",
    "gmf-runtime":       "gmf-runtime",
    "gmf runtime":       "gmf-runtime",
    "org.eclipse.mylyn": "org.eclipse.mylyn",
    "org.eclipse.rap":   "org.eclipse.rap",
    "ptp":               "ptp",
    "scout.rt":          "scout.rt",
    "webtools.javaee":   "webtools.javaee",
    "webtools":          "webtools.javaee",
    "web tools":         "webtools.javaee",
    "windowbuilder":     "windowbuilder",
    "window builder":    "windowbuilder",
    "m2e-core":          "m2e-core",
    "m2e":               "m2e-core",
    "scout":             "scout.rt",
    "emf":               "org.eclipse.emf",
    "mylyn":             "org.eclipse.mylyn",
    "rap":               "org.eclipse.rap",
    "cvs":               "eclipse.cvs",
    "subversive":        "subclipse",
    "emf (core)":        "org.eclipse.emf",
    "rap tools":         "org.eclipse.rap",
    "rap runtime":       "org.eclipse.rap",
}

# ---------------------------------------------------------------------------
# Mapeamento pasta do repositório local → Nome de exibição consolidado
# ---------------------------------------------------------------------------

DISPLAY_NAMES: dict[str, str] = {
    "eclipse.jdt.core":  "JDT",
    "eclipse.pde":       "PDE",
    "cdt":               "CDT",
    "gef-classic":       "GEF",
    "org.eclipse.emf":   "EMF",
    "birt":              "BIRT",
    "datatools":         "DataTools",
    "eclipselink":       "EclipseLink",
    "egit":              "EGit",
    "gmf-runtime":       "GMF Runtime",
    "org.eclipse.mylyn": "Mylyn",
    "org.eclipse.rap":   "RAP",
    "ptp":               "PTP",
    "scout.rt":          "Scout",
    "webtools.javaee":   "WebTools",
    "windowbuilder":     "Window Builder",
    "m2e-core":          "m2e",
    "eclipse.cvs":       "CVS",
    "subclipse":         "Subversive"
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
