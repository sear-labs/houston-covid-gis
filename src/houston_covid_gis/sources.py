r"""Every data source the original ArcGIS map used, and its current status.

The map (`gis/Covid and Health Factors.mapx`) had 25 layers and **not one byte of
local data** - every layer was a remote ArcGIS Online service URL. That makes the
source list the most important artifact of the whole thing, because two of those
services no longer exist.

ArcGIS FeatureServer endpoints speak GeoJSON, so anything still live is
`gpd.read_file(geojson_url(...))` away. No Esri licence, no ArcGIS install.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# DEAD. Confirmed removed - these are why the .mapx alone cannot be replayed.
# --------------------------------------------------------------------------
RETIRED = {
    "CITY_LIMITS_COVID": {
        "was": "https://services.arcgis.com/su8ic9KbA7PYVxPS/arcgis/rest/services"
               "/CITY_LIMITS_COVID/FeatureServer",
        "held": "per-ZIP TotalConfirmedCases / ActiveCases / Recovered / Death, "
                "and the polygons the eight regional layers selected from",
        "status": "GONE - returns 'Invalid URL'; absent from the City of Houston "
                  "org's ~1000 published services",
        "recovered_as": "data/derived/covid_by_region_zip.csv (attributes) and "
                        "data/geometry/covid_regions.gpkg (geometry)",
    },
    "Harris_Vulnerability_Census_Tracts": {
        "was": "https://services9.arcgis.com/EWJA19Qlz9w50wTU/arcgis/rest/services"
               "/Harris_Vulnerability_Census_Tracts/FeatureServer",
        "held": "a Final_Vuln composite vulnerability score per census tract",
        "status": "GONE - returns 'Invalid URL'",
        "recovered_as": "NOT RECOVERED. Substitute CDC SVI 2018 (see PUBLIC below), "
                        "which is the input it was derived from, not the layer itself.",
    },
}

# --------------------------------------------------------------------------
# LIVE third-party services. Reference these; do not vendor copies.
# --------------------------------------------------------------------------
PUBLIC = {
    "cdc_svi_2016_houston_tracts":
        "https://services.arcgis.com/NummVBqZSIJKUeVR/arcgis/rest/services"
        "/CDC_SVI_2016_Houston_Harris_County_tracts/FeatureServer/0",
    "rate_of_asthma":
        "https://services6.arcgis.com/HJzJQeO8rbTv2jiF/arcgis/rest/services"
        "/Rate_of_Asthma/FeatureServer/0",
    "healthcare_facilities":
        "https://services3.arcgis.com/ImYoiBnIj5kSaAsi/arcgis/rest/services"
        "/HealthCareFacilities/FeatureServer/0",
    "coh_neighborhood_services":
        "https://cohegis.houstontx.gov/cohgispub/rest/services/PD"
        "/Neighborhood_Services_wm/MapServer/11",
    "jhu_covid_us":
        "https://services1.arcgis.com/0MSEUqKaxRlEPj5g/arcgis/rest/services"
        "/ncov_cases_US/FeatureServer/0",
    "county_health_rankings_2019":
        "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services"
        "/County_Health_Rankings_2019/FeatureServer/0",
    "usa_counties":
        "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services"
        "/USA_Counties/FeatureServer/0",
}

# Bulk downloads rather than services. Cited, never redistributed.
DOWNLOADS = {
    "cdc_svi_2018":
        "https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html",
    "cdc_svi_2018_documentation":
        "https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/08/"
        "SVI2018Documentation_01192022_1.pdf",
    "census_tiger_zcta_2020":
        "https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/",
}

# Definition queries the original map applied, kept so a rebuild matches it.
DEFINITION_QUERIES = {
    "jhu_covid_us": "Province_State = 'Texas'",
    "county_health_rankings_2019": "STATE = 'TX'",
    "usa_counties": "STATE_NAME = 'Texas'",
}

# The proportional-symbol renderer on TotalConfirmedCases, read out of the .mapx
# so a rebuild can look like the original rather than approximating it.
PROPORTIONAL_SYMBOL = {
    "field": "TotalConfirmedCases",
    "min_size": 8.0,
    "max_size": 43.4167,
    "max_value": 562,
    "scaling": "area",
}

REGIONS = ("E", "NE", "NW", "N", "SE", "SW", "S", "W")


def geojson_url(service_url: str, where: str = "1=1", out_fields: str = "*") -> str:
    """Turn an ArcGIS FeatureServer layer URL into a GeoJSON query geopandas can read.

    >>> geojson_url(PUBLIC["rate_of_asthma"])[:60]
    'https://services6.arcgis.com/HJzJQeO8rbTv2jiF/arcgis/rest/s'
    """
    sep = "&" if "?" in service_url else "?"
    return (f"{service_url}/query{sep}where={where}"
            f"&outFields={out_fields}&outSR=4326&f=geojson")


def status_report() -> str:
    """Human-readable source audit - what still resolves and what does not."""
    lines = ["LIVE (%d):" % len(PUBLIC)]
    lines += [f"  {k}" for k in sorted(PUBLIC)]
    lines += ["", "RETIRED (%d) - the map cannot be replayed from the network:" % len(RETIRED)]
    for k, v in RETIRED.items():
        lines += [f"  {k}", f"      held:      {v['held']}",
                  f"      status:    {v['status']}", f"      recovered: {v['recovered_as']}"]
    return "\n".join(lines)
