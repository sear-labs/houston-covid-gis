"""Where the data lives. Importable without geopandas or any solver."""
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("HCG_DATA_DIR", _ROOT / "data"))
DERIVED = DATA_DIR / "derived"
GEOMETRY = DATA_DIR / "geometry"
RESULTS_DIR = Path(os.environ.get("HCG_RESULTS_DIR", _ROOT / "results"))
FIGURES = _ROOT / "figures"
