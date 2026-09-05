"""Where the data lives. Importable without geopandas or any solver."""
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("HCG_DATA_DIR", _ROOT / "data"))
DERIVED = DATA_DIR / "derived"
GEOMETRY = DATA_DIR / "geometry"
RESULTS_DIR = Path(os.environ.get("HCG_RESULTS_DIR", _ROOT / "results"))
FIGURES = _ROOT / "figures"


def check_data_dir(path=None):
    """Fail with the real reason when the data directory is not where we think.

    DATA_DIR is derived from this file's location, which is only correct inside
    a source checkout. After a plain `pip install` the package sits in
    site-packages and the derivation lands somewhere meaningless - and the data
    was never in the wheel to begin with, since it lives at the repo root. The
    naive symptom is "some_table.csv missing", which sends people looking for a
    corrupt download. Say what actually happened instead.
    """
    path = DATA_DIR if path is None else path
    if path.exists():
        return path
    raise FileNotFoundError(
        str(path) + " does not exist.\n\n"
        "The data ships with the REPOSITORY, not with the installed package, so\n"
        "`pip install git+https://...` gets you the code without it. Clone instead:\n\n"
        "    git clone https://github.com/sear-labs/houston-covid-gis.git\n"
        "    cd houston-covid-gis && pip install -e .\n\n"
        "Or point $HCG_DATA_DIR at a directory holding the data files."
    )
