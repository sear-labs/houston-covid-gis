# Houston COVID-19 GIS — NSF EAGER #2028612

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sear-labs/houston-covid-gis/blob/main/notebooks/00_walkthrough.ipynb)
[![Code DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22309109.svg)](https://doi.org/10.5281/zenodo.22309109)

The Houston COVID-19 mapping and spatial analysis from **NSF EAGER award #2028612**, *"AI-Enabled
Optimization of the COVID-19 Therapeutics Supply Chain to Support Community Public Health"*
(Erick C. Jones Jr., PI) — rebuilt in Python.

**147 ZIP codes across eight regions of Houston, 49,365 confirmed cases, 487 deaths**, with social
vulnerability, hospital access and neighborhood connectivity.

The original was an ArcGIS Pro project. This repository is a rewrite that needs **no Esri licence**,
and it is more reproducible than the original for a specific reason given below.

---

## Why this exists in this form

The original map is `gis/Covid and Health Factors.mapx`. Opening it reveals two problems.

**It contains no data.** All 25 layers were remote ArcGIS Online service URLs — not one byte of
geometry or attributes was stored locally.

**Two of those services are gone.** `CITY_LIMITS_COVID`, which held every COVID count and the
polygons the analysis was built on, now returns *"Invalid URL"* and is absent from the City of
Houston's ~1000 published services. `Harris_Vulnerability_Census_Tracts` is likewise gone.

So the `.mapx` cannot be replayed. What survived is an ArcGIS **file geodatabase** in a sibling
project folder, and that is what this repository is built from.

There is a third problem worth stating, because it is what makes the Python version *better* rather
than merely equivalent. **The eight regional layers were not defined by a rule.** They were
base64-encoded blobs holding hand-picked lists of OBJECTIDs — pointers into a service that no longer
exists, unreadable without Esri software and meaningless once the service died. Here the region is
an ordinary column in an ordinary file.

## Run it

```bash
pip install -e ".[dev]"        # tables + connectivity: pandas and networkx only
pytest -q
```

For the geometry and maps you also need the geospatial stack:

```bash
conda env create -f environment.yml && conda activate houston-gis
python scripts/convert_geometry.py     # .gdb -> GeoPackage, run once
```

The split is deliberate: **the analysis runs anywhere pandas does.** Only reading the original
geodatabases and drawing maps needs GDAL.

## What is here

```
data/geometry/covid_regions.gpkg   AUTHORITATIVE. 8 region layers, geometry + case counts.
data/geometry/points.gpkg          distribution centres, pharmacies
data/derived/                      tabular views, all generated from the above or Erick's own exports
gis/                               the original .mapx and .lyrx, as provenance
figures/                           27 rendered maps from the original project
src/houston_covid_gis/
    sources.py       every original layer URL, live or dead, with what each held
    tables.py        load the derived tables
    connectivity.py  graph analysis, replacing ArcGIS Network Analyst
scripts/convert_geometry.py        .gdb -> GeoPackage
```

GeoPackage rather than shapefile: no 10-character field truncation, one file instead of a seven-file
sidecar set that breaks when one member goes missing, and geometry, attributes and CRS together.

## ⚠ The exported spreadsheets disagree with the geodatabase

The project also contains eight `*_COVID_TableToExcel.xlsx` exports. **They do not agree with the
geodatabase**, and the difference is not small:

| | ZIPs | confirmed cases |
|---|---:|---:|
| `covid_regions.gpkg` (authoritative) | 147 | 49,365 |
| the xlsx exports (`legacy_2020_region_exports.csv`) | 116 | 13,954 |

The disagreement is in the **region assignment**, not just the totals. For region W the two share
2 ZIPs out of 22. For **S and SE they share none at all** — the exports put 2 ZIPs in S where the
geodatabase has 17.

The exports look like an early-pandemic extract taken before the regions were finalised. They are
kept as `data/derived/legacy_2020_region_exports.csv` for provenance and **should not be used as
data**. Everything in `data/derived/covid_by_region_zip.csv` is generated from the geodatabase, so
the table and the geometry cannot drift apart.

## Connectivity: ArcGIS Network Analyst was never needed

Two ArcGIS tools were used, and conflating them is easy:

**`Generate Near Table` does no routing.** Despite the branding, it measures straight-line distance.
That is why `super_neighborhood_distances.csv` — a complete 88×88 matrix — is reproducible with
`scipy.spatial.cKDTree`, and why `connectivity.py` needs nothing but `networkx`.

A percolation sweep over that matrix, which the original could not produce:

| threshold | components | largest | isolated |
|---:|---:|---:|---:|
| 1.05 mi | 87 | 2 | 86 |
| 4.54 mi | 7 | 82 | 6 |
| 8.03 mi | 2 | 86 | 0 |
| **11.52 mi** | **1** | **88** | **0** |

Houston's 88 super neighborhoods coalesce into one connected system at about 11.5 miles.

**`Find Nearest` on ArcGIS Online genuinely does route**, over Esri's street network. That one is
*not* reproduced. OSMnx, OpenRouteService, Valhalla and OSRM give comparable network distances but
over a different network with a different speed model, so they will not match. `nearest_hospital.csv`
is kept as recorded output rather than regenerated — do not diff it against a rebuild and expect
agreement.

*Distance units:* the matrix records no CRS. Values run 5,518–189,825, and 189,825 ≈ 36 miles, which
fits Houston if the unit is US survey feet — the linear unit of the Texas State Plane zones. Treated
as feet throughout, flagged because it is inference from magnitude, not a stated unit.

## Data provenance

**Erick's own derived work** — the geodatabases, `svi_by_zip.csv` (his tract→ZIP spatial join, not a
CDC product), `super_neighborhood_distances.csv`, the hospital-distance tables, `zip_populations.csv`.

**Public third-party, referenced not redistributed** — CDC/ATSDR Social Vulnerability Index, Census
TIGER ZCTA boundaries, Esri Living Atlas, JHU COVID-19 US cases, City of Houston services. Every URL
is in `src/houston_covid_gis/sources.py`; `sources.status_report()` prints what still resolves.

**Excluded, and permanently.** `Information Tables/Health Data/Every Case by Demographic and
ZipCode` is **154,767 rows — one per person** — carrying `X`/`Y` point coordinates alongside race,
gender, age band and symptom date. It is governed by the project IRB and the Houston Health
Department data-use agreement. It is not in this repository, it is in `.gitignore`, and
`tests/test_data_integrity.py` fails if any file here grows individual-level columns.

Also excluded: the project folder's carbon-capture GIS (`GulfCoastCarbonShed`, `Sinks`,
`MyProject*`), which belongs to unrelated SimCCS work and carries ESRI Data & Maps and PHMSA layers
that **cannot be redistributed**.

## Known data-quality issues

- `zip_to_hospital_distances.csv` — 66 of 294 rows have `Total_Miles == 0.0`. Most are a hospital
  inside the origin ZIP, which is legitimate, but the value is not a measured distance. Filter
  before using it quantitatively.
- `Harris_Vulnerability_Census_Tracts` was never recovered. CDC SVI 2018 is the input it derived
  from, not the layer itself.

## How to cite

Cite **the paper** for the work and **this repository** for the code.

```bibtex
@article{jones2021lastmile,
  author  = {Jones, Erick C. and Azeem, Gohar and Jones, Jr., Erick C. and
             Jefferson, Felicia and Henry, Marcia and Abolmaali, Shannon and
             Sparks, Janice},
  title   = {Understanding the Last Mile Transportation Concept Impacting
             Underserved Global Communities to Save Lives During COVID-19 Pandemic},
  journal = {Frontiers in Future Transportation},
  year    = {2021},
  doi     = {10.3389/ffutr.2021.732331}
}
```

**Code DOI:** [10.5281/zenodo.22309109](https://doi.org/10.5281/zenodo.22309109) — this is the *concept* DOI. It always resolves
to the latest version and never changes, so it is the one to cite. The v1.0.0 release
additionally has its own version DOI, 10.5281/zenodo.22309110, if you need to pin an exact release.

`CITATION.cff` in the repo root also gives GitHub's "Cite this repository" button.

## Related

This is **not** the project behind *"Analyzing the Connectivity of Combined Statistical Areas in
Different Census Regions Using ArcGIS"* (ISCTJ 2023). That is separate work at a different scale —
it mentions COVID, Houston, SVI and ZIP codes zero times — and its ArcGIS project is not in this
folder.

The optimisation model from the same award is a separate repository.
