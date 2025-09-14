import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path

from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
from sphere.flood.default_vulnerability import DefaultFloodVulnerability
from .conftest import DummyBuildingPoints
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader


class SimpleDepthGrid(AbstractRasterReader):
    def __init__(self, depth_value: float):
        self.depth_value = depth_value

    def get_value(self, lon: float, lat: float) -> float:
        return self.depth_value

    def get_value_vectorized(self, geometry):
        return np.full(len(geometry), self.depth_value)


def _read_lookup_tables():
    base = Path("packages") / "data" / "src" / "sphere" / "data"
    xdf = pd.read_csv(base / "flDmgXRef.csv")
    bdf = pd.read_csv(base / "flBldgDmgFn.csv")
    # set index for easier lookup
    bdf = bdf.set_index("BldgDmgFnId")
    return xdf, bdf


def test_expected_damage_for_selected_occupancies():
    """Integration test: for a set of occupancies expect known building damage at 5ft depth_in_structure."""
    # Choose occupancy types to exercise different lookups
    occupancies = ["RES3E", "IND2", "COM1", "EDU1", "RES1"]

    # Build rows for each occupancy. Use first_floor_height=1 and flood_depth=6 -> depth_in_structure=5
    rows = []
    for i, occ in enumerate(occupancies, start=1):
        rows.append(
            {
                "Id": i,
                "OccupancyType": occ,
                "Cost": 100000.0,
                "NumStories": 1,
                "FoundationType": 7,  # maps to no-basement
                "FirstFloorHt": 1,
                "Area": 1000,
                "Longitude": -157.7 - i * 0.01,
                "Latitude": 21.3 + i * 0.01,
                "ContentCostUSD": 50000.0,
                "BDDF_ID": 0,
                "CDDF_ID": 0,
                "IDDF_ID": 0,
            }
        )

    df = pd.DataFrame(rows)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")
    buildings = DummyBuildingPoints(gdf=gdf)

    # Use Default vulnerability and a depth grid that produces 6.0 flood depth
    vuln = DefaultFloodVulnerability(buildings=buildings, flood_type="R")
    depth_grid = SimpleDepthGrid(6.0)

    analysis = HazusFloodAnalysis(buildings=buildings, vulnerability_func=vuln, depth_grid=depth_grid)
    analysis.calculate_losses()

    # Read lookup tables to compute expected bldg damage at depth_in_structure == 5
    xdf, bdf = _read_lookup_tables()

    # For each building, determine the BldgDmgFnId chosen by the vulnerability logic
    result = buildings.gdf
    for idx, row in result.iterrows():
        occ = row[buildings.fields.get_field_name("occupancy_type")]
        stories = row[buildings.fields.get_field_name("number_stories")]
        basement = 0  # we used FoundationType 7 -> not in ['B',4]

        # Find matching xdf entry for hazard R
        candidates = xdf[
            (xdf["Occupancy"] == occ) &
            (xdf["Basement"] == basement) &
            (xdf["HazardR"] == 1) &
            (xdf["StoriesMin"] <= stories) &
            (xdf["StoriesMax"] > stories)
        ]

        assert not candidates.empty, f"No cross-ref found for occupancy {occ}"
        bdf_id = int(candidates.iloc[0]["BldgDmgFnId"])

        # Expect the building damage percent to match the 'ft05' column (depth_in_structure=5)
        expected = float(bdf.loc[bdf_id]["ft05"])
        actual = float(row[buildings.fields.get_field_name("building_damage_percent")])

        assert np.isclose(actual, expected, atol=1e-6), f"Occupancy {occ}: expected {expected}, got {actual}"


def test_depth_greater_than_24_caps_at_100_percent():
    """Ensure deep flooding (>24 ft) results in 100% building damage for a lookup that reaches 100 at ft24."""
    xdf, bdf = _read_lookup_tables()

    # Find a BldgDmgFnId that has 100 at ft24 and has at least one matching occupancy entry
    candidates_bdf = bdf[bdf["ft24"] >= 99.999]
    assert not candidates_bdf.empty

    chosen_id = int(candidates_bdf.index[0])

    # Find an xdf row that references a bdf id with ft24 >= 100
    xrow = None
    for _, xr in xdf.iterrows():
        bid = xr["BldgDmgFnId"]
        if pd.isna(bid):
            continue
        bid = int(bid)
        if bid in bdf.index and float(bdf.loc[bid]["ft24"]) >= 99.999:
            xrow = xr
            break

    assert xrow is not None, "Could not find cross-reference to a damage function with ft24=100"
    occ = xrow["Occupancy"]
    # determine a number of stories and foundation type consistent with the xdf entry
    stories_min = int(xrow["StoriesMin"])
    stories_max = int(xrow["StoriesMax"]) if pd.notna(xrow["StoriesMax"]) else stories_min + 1
    chosen_stories = max(1, stories_min)
    basement_flag = int(xrow["Basement"]) if pd.notna(xrow["Basement"]) else 0
    foundation_type = 4 if basement_flag == 1 else 7

    # Create a single building with deep flooding (depth_in_structure > 24)
    df = pd.DataFrame([
        {
            "Id": 1,
            "OccupancyType": occ,
            "Cost": 100000.0,
            "NumStories": chosen_stories,
            "FoundationType": foundation_type,
            "FirstFloorHt": 1,
            "Area": 1000,
            "Longitude": -157.7,
            "Latitude": 21.3,
            "ContentCostUSD": 50000.0,
            "BDDF_ID": 0,
            "CDDF_ID": 0,
            "IDDF_ID": 0,
        }
    ])
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")
    buildings = DummyBuildingPoints(gdf=gdf)

    # Use depth grid that yields flood_depth such that depth_in_structure = 30
    depth_grid = SimpleDepthGrid(31.0)
    vuln = DefaultFloodVulnerability(buildings=buildings, flood_type="R")
    analysis = HazusFloodAnalysis(buildings=buildings, vulnerability_func=vuln, depth_grid=depth_grid)
    analysis.calculate_losses()

    result = buildings.gdf.iloc[0]
    bldg_pct = float(result[buildings.fields.get_field_name("building_damage_percent")])

    assert bldg_pct >= 99.99, f"Expected ~100% damage for deep flooding, got {bldg_pct}"
