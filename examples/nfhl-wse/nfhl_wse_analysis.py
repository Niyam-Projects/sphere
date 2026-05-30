"""
NFHL WSE-Based Flood Loss Analysis — Harris County, TX
======================================================
Demonstrates overriding the hazard step in HazusFloodAnalysis to derive
flood depth from a Water Surface Elevation (WSE) raster instead of a
pre-computed depth raster.

Depth derivation:
    depth             = WSE_raster_value - ground_elv  (ground elevation from NSI)
    depth_in_structure = depth - found_ht              (first floor height from NSI)

All downstream calculations (vulnerability lookup, loss, debris, restoration)
are inherited unchanged from HazusFloodAnalysis.
"""

import time
import pandas as pd
import geopandas as gpd
from pathlib import Path

from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
from sphere.flood.single_value_reader import SingleValueRaster
from sphere.flood.default_vulnerability import DefaultFloodVulnerability
from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.nsi_buildings import NsiBuildings


# ---------------------------------------------------------------------------
# Custom analyzer: swap depth-raster for WSE-raster + ground subtraction
# ---------------------------------------------------------------------------

class WseHazusFloodAnalysis(HazusFloodAnalysis):
    """
    HazusFloodAnalysis variant that derives depth from a WSE raster.

    Pass the WSE raster as ``depth_grid``. The override of
    ``_compute_flood_depth`` subtracts each building's ground elevation
    (``grnd_elv`` from NSI) from the sampled WSE value, yielding the depth
    of water above ground at that structure.
    """

    def _compute_flood_depth(self, gdf: gpd.GeoDataFrame) -> pd.Series:
        """
        Derive depth by sampling the WSE raster then subtracting ground elevation.

        Steps:
            1. Sample WSE raster at each building's point geometry.
            2. Subtract ``ground_elv`` (NAVD88 ground elevation in feet) from NSI.

        Returns:
            pd.Series of depth values (ft). NaN where WSE is NoData or the
            building falls outside the raster extent.
        """
        wse_values = pd.Series(
            self.depth_grid.get_value_vectorized(gdf.geometry),
            index=gdf.index,
        )
        return wse_values - gdf["ground_elv"]


# ---------------------------------------------------------------------------
# Helper: load & spatially subset NSI to Harris County
# ---------------------------------------------------------------------------

def load_harris_county_nsi(gpkg_path: str) -> NsiBuildings:
    """
    Load NSI from a Texas state geopackage and filter to Harris County.

    Harris County FIPS: 48201. The NSI ``county`` column stores the 5-digit
    integer FIPS code. Pre-processing mirrors NsiBuildings so the Buildings
    field mapping resolves correctly.
    """
    print(f"Loading NSI from {gpkg_path} ...")
    t0 = time.time()

    gdf = gpd.read_file(gpkg_path, layer="nsi")
    # Performance tip: if pyogrio is installed, use a filtered read to avoid
    # loading all ~1.5M Texas structures into memory:
    #   gdf = gpd.read_file(gpkg_path, layer="nsi", where="county = 48201")

    harris_fips = "48201"
    if "cbfips" in gdf.columns:
        # cbfips is the census block FIPS (e.g. "482011234560001"); the first 5 digits
        # are the state+county FIPS, so filter to Harris County (48201) with startswith.
        gdf = gdf[gdf["cbfips"].astype(str).str.startswith(harris_fips)].reset_index(drop=True)
    elif "county" in gdf.columns:
        gdf = gdf[gdf["county"] == int(harris_fips)].reset_index(drop=True)
    else:
        raise KeyError(
            f"No county identifier column found in NSI layer. "
            f"Expected 'cbfips' or 'county'. "
            f"Available columns: {list(gdf.columns)}"
        )
    print(f"  Harris County structures: {len(gdf):,}  ({time.time() - t0:.1f}s)")

    # Strip sub-type suffix after dash (e.g. "RES1-1SNB" → "RES1")
    if "occtype" in gdf.columns:
        gdf["occtype"] = gdf["occtype"].astype(str).str.split("-", n=1).str[0]

    # Note: do NOT add a 'foundation_type' column here. The Buildings field mapping
    # resolves 'foundation_type' via the alias 'found_type' (numeric 1-7), which is
    # what the debris and vulnerability calculations expect. Adding a letter-code
    # 'foundation_type' column would shadow the numeric values and break debris lookups.

    # Build a NsiBuildings instance from the already-filtered GeoDataFrame by
    # bypassing the file-loading constructor and calling the Buildings base init.
    buildings = object.__new__(NsiBuildings)
    Buildings.__init__(buildings, gdf)
    return buildings


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_nfhl_wse():
    start = time.time()

    nsi_gpkg = "E:/projects/asfpm2026/nsi_2022_48.gpkg"
    wse_tif  = "E:/projects/asfpm2026/harris_county_wse_cog.tif"
    results_file = Path("E:/projects/asfpm2026/sphere_harris_wse_results.parquet")

    # Load Harris County structures from the Texas state GPKG
    buildings = load_harris_county_nsi(nsi_gpkg)

    # Open WSE raster (Cloud Optimized GeoTIFF reads tile-by-tile for efficiency)
    print(f"Opening WSE raster: {wse_tif}")
    wse_grid = SingleValueRaster(wse_tif)

    # Flood vulnerability function (Riverine)
    flood_function = DefaultFloodVulnerability(buildings, flood_type="R")

    # WSE-based analyzer — depth override, all other logic inherited unchanged
    analyzer = WseHazusFloodAnalysis(
        buildings=buildings,
        vulnerability_func=flood_function,
        depth_grid=wse_grid,
    )

    print("Running loss calculation ...")
    analyzer.calculate_losses()

    buildings.gdf.to_parquet(results_file, compression="zstd")

    elapsed = time.time() - start
    print(f"Execution time: {elapsed:.1f}s")
    print(f"Analysis complete for {len(buildings.gdf):,} structures. "
          f"Results saved to: {results_file}")


if __name__ == "__main__":
    run_nfhl_wse()
