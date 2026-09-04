r"""Assert the things that must be true of this dataset.

There is no published number to reconcile against here - the ArcGIS map was
never a paper - so what these tests defend is internal consistency and the
absence of restricted data.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from houston_covid_gis import sources, tables  # noqa: E402

EXPECTED_ZIPS = 147
EXPECTED_CASES = 49365
EXPECTED_DEATHS = 487


def test_regions_partition_cleanly():
    """Every ZIP belongs to exactly one region - no overlap, no gaps."""
    df = tables.covid_by_region_zip()
    assert len(df) == EXPECTED_ZIPS
    assert df["ZIP"].duplicated().sum() == 0, "a ZIP appears in two regions"
    assert set(df["Region"]) == set(sources.REGIONS)


def test_totals_match_the_geodatabase():
    df = tables.covid_by_region_zip()
    assert int(df["TotalConfirmedCases"].sum()) == EXPECTED_CASES
    assert int(df["Death"].sum()) == EXPECTED_DEATHS


def test_counts_are_internally_consistent():
    """Active + Recovered should not exceed confirmed, and nothing is negative."""
    df = tables.covid_by_region_zip()
    for c in ("TotalConfirmedCases", "ActiveCases", "Recovered", "Death"):
        assert (df[c] >= 0).all(), f"{c} has negative values"
    over = df[df["ActiveCases"] + df["Recovered"] > df["TotalConfirmedCases"] + 1]
    assert over.empty, f"{len(over)} ZIPs have Active+Recovered > Confirmed"


def test_legacy_snapshot_is_kept_and_differs():
    """The earlier export is preserved AND is documented as disagreeing."""
    legacy = tables.legacy_region_exports()
    auth = tables.covid_by_region_zip()
    assert len(legacy) < len(auth), "the legacy snapshot should be the smaller one"
    assert legacy["TotalConfirmedCases"].sum() < auth["TotalConfirmedCases"].sum()
    assert tables.legacy_region_exports.__doc__ and \
        "disagree" in tables.legacy_region_exports.__doc__.lower(), \
        "the disagreement must stay documented in the docstring"


def test_no_restricted_data_present():
    """The individual-level case file must never appear in this repository.

    Information Tables/Health Data/Every Case by Demographic and ZipCode is
    154,767 rows, one per person, geocoded to X/Y with race, gender and age
    band. It is governed by the project IRB and the HHD data-use agreement.
    """
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    banned_cols = {"gender", "agerange", "race", "datesymptoms", "hospitalized"}
    for dirpath, _, files in os.walk(os.path.join(root, "data")):
        for f in files:
            if not f.lower().endswith(".csv"):
                continue
            cols = {c.strip().lower() for c in
                    pd.read_csv(os.path.join(dirpath, f), nrows=0).columns}
            leaked = cols & banned_cols
            assert not leaked, f"{f} carries individual-level columns: {leaked}"


def test_every_live_source_is_a_query_url():
    for name, url in sources.PUBLIC.items():
        q = sources.geojson_url(url)
        assert q.startswith("https://") and "f=geojson" in q and "outSR=4326" in q


def test_retired_sources_are_documented_not_silently_dropped():
    """A dead layer must say what it held and how it was recovered."""
    assert sources.RETIRED, "the retired services must stay recorded"
    for name, meta in sources.RETIRED.items():
        for key in ("was", "held", "status", "recovered_as"):
            assert meta.get(key), f"{name} is missing '{key}'"


def test_connectivity_needs_no_arcgis():
    """The distance matrix is planar Euclidean, so plain graph tools suffice."""
    from houston_covid_gis import connectivity
    g = connectivity.distance_graph()
    assert g.number_of_nodes() == 88
    assert g.number_of_edges() == 88 * 87 // 2, "the Near Table should be complete"
    sweep = connectivity.percolation_sweep(4)
    assert sweep["components"].iloc[0] > sweep["components"].iloc[-1], \
        "raising the threshold should merge components"
    assert sweep["largest_component"].iloc[-1] == 88
