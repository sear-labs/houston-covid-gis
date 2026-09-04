r"""Connectivity analysis in networkx, replacing ArcGIS Network Analyst.

The original workflow used ArcGIS's proximity toolset. Two of those tools are
being replaced here, and it matters which is which:

  Generate Near Table  ->  PLANAR EUCLIDEAN nearest-neighbour.
      Despite the "Network" branding elsewhere in ArcGIS, this tool does no
      routing at all - it measures straight-line distance between geometries.
      That is why `super_neighborhood_distances.csv` can be reproduced exactly
      with scipy.spatial.cKDTree, and why nothing in this module needs a routing
      engine or an Esri licence.

  ArcGIS Online "Find Nearest"  ->  genuinely ROUTED over Esri's street network.
      This one is NOT reproduced here. OSMnx, OpenRouteService, Valhalla and
      OSRM all give network distance and travel time, but over a different
      network with a different speed model, so they will not match Esri's
      numbers. `nearest_hospital.csv` is kept as recorded output rather than
      regenerated - see tables.nearest_hospital().

Everything below runs on the shipped 88x88 distance matrix. No network calls.
"""
from __future__ import annotations

import networkx as nx
import pandas as pd

from .tables import super_neighborhood_distances


# NEAR_DIST units. The values run 5,518 to 189,825 over Houston super
# neighborhoods; 189,825 is about 36 miles, which fits the city's extent if the
# unit is US survey feet - the linear unit of the Texas State Plane zones ArcGIS
# defaults to here. Treated as feet below, flagged because the source table
# records no CRS and this is inference from magnitude, not a stated unit.
FEET_PER_MILE = 5280.0


def distance_graph(max_rank: int | None = None,
                   max_distance: float | None = None) -> nx.Graph:
    """Build a weighted graph of super neighborhoods from the distance matrix.

    `max_rank` keeps only each node's k nearest neighbours (a k-NN graph);
    `max_distance` keeps only edges under a threshold. Passing neither gives the
    complete graph, which is what the Near Table actually is.
    """
    df = super_neighborhood_distances()
    if max_rank is not None and "NEAR_RANK" in df.columns:
        df = df[df["NEAR_RANK"] <= max_rank]
    if max_distance is not None:
        df = df[df["NEAR_DIST"] <= max_distance]

    g = nx.Graph()
    # Add every node first. Otherwise a threshold that isolates a neighborhood
    # drops it from the graph entirely and the component count silently lies.
    full = super_neighborhood_distances()
    g.add_nodes_from(pd.unique(pd.concat([full["IN_FID"], full["NEAR_FID"]]).astype(int)))
    for r in df.itertuples(index=False):
        u, v, w = int(r.IN_FID), int(r.NEAR_FID), float(r.NEAR_DIST)
        # The matrix holds both directions; keep the shorter if they disagree.
        if g.has_edge(u, v):
            if w < g[u][v]["weight"]:
                g[u][v]["weight"] = w
        else:
            g.add_edge(u, v, weight=w)
    return g


def centrality(max_rank: int = 5) -> pd.DataFrame:
    """Rank neighborhoods by how central they are in the k-NN adjacency.

    This is the question the ArcGIS workflow was circling - which areas are
    structurally well connected - and it is ordinary graph theory.
    """
    g = distance_graph(max_rank=max_rank)
    deg = nx.degree_centrality(g)
    btw = nx.betweenness_centrality(g, weight="weight")
    clo = nx.closeness_centrality(g, distance="weight")
    out = pd.DataFrame({
        "degree_centrality": pd.Series(deg),
        "betweenness_centrality": pd.Series(btw),
        # Closeness is 1/sum(distance), so in feet it comes out around 1e-6 and
        # reads as 0.0 at any sane rounding. Rescale to miles so the column is
        # legible; the ORDERING is identical either way.
        "closeness_centrality_per_mile": pd.Series(clo) * FEET_PER_MILE,
    })
    out.index.name = "SN_FID"
    return out.sort_values("betweenness_centrality", ascending=False)


def minimum_spanning_tree() -> nx.Graph:
    """MST over the complete distance graph - the cheapest connecting backbone."""
    return nx.minimum_spanning_tree(distance_graph(), weight="weight")


def components(max_distance: float) -> list[set]:
    """Connected components when only links under `max_distance` count.

    Sweeping the threshold shows at what distance the city coalesces into one
    connected system - a percolation view the original map could not produce.
    """
    return [set(c) for c in nx.connected_components(distance_graph(max_distance=max_distance))]


def percolation_sweep(steps: int = 12) -> pd.DataFrame:
    """At each distance threshold: how many components, and how big the largest.

    The single most useful thing this module does that ArcGIS did not.
    """
    df = super_neighborhood_distances()
    lo, hi = df["NEAR_DIST"].min(), df["NEAR_DIST"].max()
    rows = []
    for i in range(steps + 1):
        # Start AT the minimum, where almost nothing is linked yet, so the sweep
        # actually shows the city coalescing instead of starting connected.
        t = lo + (hi - lo) * i / steps
        comps = components(t)
        rows.append({"threshold_ft": round(t, 1),
                     "threshold_mi": round(t / FEET_PER_MILE, 2),
                     "components": len(comps),
                     "largest_component": max((len(c) for c in comps), default=0),
                     "isolated": sum(1 for c in comps if len(c) == 1)})
    return pd.DataFrame(rows)
