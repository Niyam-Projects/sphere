import pandas as pd
import geopandas as gpd
from sphere.core.schemas.buildings import Buildings


def test_buildings_field_mapping_and_output_creation():
    # Create a minimal GeoDataFrame with common field names that should be discovered
    df = pd.DataFrame({
        "building_id": [1, 2, 3],
        "occupancy_type": ["RES1", "IND2", "RES3"],
        "first_floor_height": [1.0, 0.5, 2.0],
        "foundation_type": [7, 4, "B"],
        "number_stories": [1, 2, 3],
        "area": [1000, 2000, 1500],
        "building_cost": [100000, 250000, 150000],
        "content_cost": [50000, 100000, 75000],
        "inventory_cost": [0.0, 1000.0, 0.0],
        "Longitude": [-157.0, -157.1, -157.2],
        "Latitude": [21.0, 21.1, 21.2],
    })

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")

    buildings = Buildings(gdf)

    # Verify that input field names were auto-discovered
    assert buildings.fields.get_field_name("id") in gdf.columns
    assert buildings.fields.get_field_name("occupancy_type") == "occupancy_type"
    assert buildings.fields.get_field_name("first_floor_height") == "first_floor_height"

    # Accessing input properties returns underlying series
    assert buildings.id.equals(gdf[buildings.fields.get_field_name("id")])
    assert buildings.occupancy_type.equals(gdf[buildings.fields.get_field_name("occupancy_type")])

    # Output fields should be created on set
    fd = pd.Series([0.5, 1.0, 0.0])
    buildings.flood_depth = fd
    # Column name returned by mapping
    flood_col = buildings.fields.get_field_name("flood_depth")
    assert flood_col in buildings.gdf.columns
    # Values preserved
    assert buildings.gdf[flood_col].tolist() == [0.5, 1.0, 0.0]
