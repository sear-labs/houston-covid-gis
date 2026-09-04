r"""Convert the surviving ArcGIS file geodatabases to GeoPackage.

Run once. Needs geopandas; the rest of the package does not.

WHY THIS MATTERS. The map's COVID layer service is dead, so these geodatabases
hold the ONLY surviving geometry for the eight regional layers. Everything else
about the map can be rebuilt from live public services; this cannot.

WHY GEOPACKAGE, not shapefile:
  - no 10-character field-name truncation
  - one file instead of a 7-file .shp/.shx/.dbf/.prj/.sbn/.sbx/.cpg sidecar set
    that silently breaks when one member goes missing
  - geometry and attributes together, with a real CRS
  - readable by QGIS, ArcGIS, geopandas, GDAL - no Esri licence anywhere

Reading .gdb needs no Esri licence either: GDAL's OpenFileGDB driver handles it.

    conda run -n houston-gis python scripts/convert_geometry.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import geopandas as gpd

EAGER = Path(os.path.expanduser("~")) / "OneDrive - UT Arlington" / "Documents" / \
    "Projects" / "Old" / "2020 - 2023 NSF Eager Houston COVID-19 Project (2020-23)"
PROJECTS = EAGER / "Map Files" / "ArcGIS" / "Projects"
OUT = Path(__file__).resolve().parents[1] / "data" / "geometry"

JOBS = [
    (PROJECTS / "COVID2" / "Default.gdb", "covid_regions.gpkg",
     "the eight regional COVID polygons - the only surviving geometry"),
    (PROJECTS / "COVID2" / "Points.gdb", "points.gpkg",
     "distribution centres and pharmacies"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for gdb, out_name, what in JOBS:
        print("=" * 70)
        print(f"{gdb.name}  ->  {out_name}")
        print(f"  ({what})")
        if not gdb.exists():
            print("  ! missing, skipping")
            continue
        try:
            layers = gpd.list_layers(gdb)
        except Exception as e:
            print(f"  ! cannot list layers: {type(e).__name__}: {e}")
            continue

        dst = OUT / out_name
        if dst.exists():
            dst.unlink()
        written = 0
        for name in layers["name"]:
            try:
                gdf = gpd.read_file(gdb, layer=name)
            except Exception as e:
                print(f"  ! {name}: {type(e).__name__}: {str(e)[:70]}")
                continue
            if gdf.empty:
                print(f"    {name:34} empty, skipped")
                continue
            # Region layers are named like 'NEOutline_Outputtable'. Carry the
            # region code as a column so downstream code never has to parse a
            # layer name to know which region it is looking at.
            layer_out = name
            if name.endswith("Outline_Outputtable"):
                gdf.insert(0, "Region", name.replace("Outline_Outputtable", ""))
                layer_out = "region_" + name.replace("Outline_Outputtable", "").lower()
            gdf.to_file(dst, layer=layer_out, driver="GPKG")
            written += 1
            total += 1
            print(f"    {name:34} -> {layer_out:16} {len(gdf):4} feat  "
                  f"{gdf.geometry.geom_type.iloc[0]:12} CRS={gdf.crs.to_string() if gdf.crs else '(none)'}")
        print(f"  wrote {written} layer(s), {dst.stat().st_size:,} B" if written
              else "  nothing written")
    print("=" * 70)
    print(f"{total} layers converted into {OUT}")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
