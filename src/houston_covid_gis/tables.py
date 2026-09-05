r"""Load the derived tables. Pandas only - no geopandas, no GDAL, no ArcGIS.

Everything here is Erick's own derived output, recovered from ArcGIS exports.
None of it is third-party data and none of it is restricted: the per-ZIP COVID
counts are aggregate, and the individual-level case file that governs this
project's IRB is deliberately not in this repository.
"""
from __future__ import annotations

import pandas as pd

from .paths import DERIVED, check_data_dir


def _csv(name: str) -> pd.DataFrame:
    """One door to the derived tier, so a missing data directory is
    reported once and accurately rather than seven times as a bare
    "no such file"."""
    check_data_dir(DERIVED)
    return pd.read_csv(DERIVED / name)


def covid_by_region_zip() -> pd.DataFrame:
    """Per-ZIP COVID counts with the region each ZIP belongs to. AUTHORITATIVE.

    Generated from `data/geometry/covid_regions.gpkg` by
    `scripts/convert_geometry.py`, so the table and the geometry can never
    disagree - they have one source. 147 ZIPs partitioned across eight regions
    with no overlap, 49,365 confirmed cases, 487 deaths.

    The original map defined its regional layers as base64 blobs holding lists
    of OBJECTIDs that pointed into a service which no longer exists. The
    geodatabase is what survived, and it carries BOTH the polygons and the case
    attributes - so the rebuild ends up more reproducible than the ArcGIS
    original, where the region assignment was unreadable without Esri software.

    See legacy_region_exports() for the earlier snapshot and why it disagrees.
    """
    return _csv("covid_by_region_zip.csv")


def legacy_region_exports() -> pd.DataFrame:
    """An EARLIER, partial snapshot of the same thing. Kept for provenance only.

    These are the eight `*_COVID_TableToExcel.xlsx` files exported from ArcGIS.
    They do NOT agree with the geodatabase and should not be used as data:

        this table      116 ZIPs, 13,954 cases
        geodatabase     147 ZIPs, 49,365 cases

    The disagreement is in the region assignment, not just the totals. For
    region W the two share 2 ZIPs out of 22; for S and SE they share NONE - the
    exports put 2 ZIPs in S where the geodatabase has 17. The exports look like
    an early-pandemic extract taken before the regions were finalised.

    Kept because it is the only record of that earlier state, and because
    anyone comparing this repo against the original spreadsheets deserves to
    find the discrepancy documented rather than discover it themselves.
    """
    return _csv("legacy_2020_region_exports.csv")


def svi_by_zip() -> pd.DataFrame:
    """CDC SVI themes joined onto ZIP codes - Erick's spatial join, not a CDC product.

    The Join_Count / TARGET_FID / JOIN_FID columns are the signature of an
    ArcGIS spatial join, so this is a tract->ZIP crosswalk he produced. The
    upstream CDC tract file is referenced in sources.DOWNLOADS rather than
    vendored here.
    """
    return _csv("svi_by_zip.csv")


def super_neighborhood_distances() -> pd.DataFrame:
    """Complete 88x88 pairwise distance matrix over Houston super neighborhoods.

    Produced by ArcGIS 'Generate Near Table', which is PLANAR EUCLIDEAN - not
    routed. That matters: it means scipy.spatial.cKDTree reproduces it exactly,
    with no ArcGIS and no routing engine. See connectivity.py.
    """
    return _csv("super_neighborhood_distances.csv")


def nearest_hospital() -> pd.DataFrame:
    """Neighborhood -> nearest hospitals, ranked.

    CAUTION: this came from ArcGIS Online's 'Find Nearest' service, which routes
    over Esri's street network. An open-source rebuild (OSMnx, ORS, Valhalla)
    gives comparable network distances but WILL NOT match these numbers to the
    decimal - different network, different speed model. Treat as recorded
    output, not as something to regenerate and diff.
    """
    return _csv("nearest_hospital.csv")


def zip_to_hospital_distances() -> pd.DataFrame:
    """ZIP -> hospital distances with per-ZIP COVID counts stamped 2020-11-17.

    CAUTION: 66 of 294 rows carry Total_Miles == 0.0. Most are a hospital inside
    the origin ZIP, which is legitimate, but the value is not a measured
    distance. Filter before using this for anything quantitative.
    """
    return _csv("zip_to_hospital_distances.csv")


def zip_populations() -> pd.DataFrame:
    """ZIP populations 2018/2019. Six empty insurance-carrier columns removed."""
    return _csv("zip_populations.csv")


def regional_summary() -> pd.DataFrame:
    """Roll the per-ZIP counts up to the eight regions - the map's headline view."""
    df = covid_by_region_zip()
    cols = [c for c in ("TotalConfirmedCases", "ActiveCases", "Recovered", "Death")
            if c in df.columns]
    out = df.groupby("Region")[cols].sum()
    out["ZIPs"] = df.groupby("Region").size()
    if "TotalConfirmedCases" in out and "Death" in out:
        out["CaseFatalityPct"] = (100 * out["Death"] / out["TotalConfirmedCases"]).round(2)
    return out.sort_values("TotalConfirmedCases", ascending=False)
