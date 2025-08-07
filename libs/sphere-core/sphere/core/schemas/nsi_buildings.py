import os
from typing import Dict
import geopandas as gpd
import pandas as pd
from sphere.core.schemas.buildings import Buildings

class NsiBuildings(Buildings):
    """
    NSI (National Structure Inventory) buildings class with geopackage loading and preprocessing.
    """
    
    def __init__(self, gpkg_file: str, layer_name: str = "nsi", overrides: Dict[str, str] | None = None):
        # If gpkg_file does not have a drive letter, assume relative to cwd.
        drive, _ = os.path.splitdrive(gpkg_file)
        if not drive:
            gpkg_path = os.path.join(os.getcwd(), gpkg_file)
        else:
            gpkg_path = gpkg_file

        # Load the GeoDataFrame from the GeoPackage file
        try:
            gdf = gpd.read_file(gpkg_path, layer=layer_name)
            
            # Pre-process the occupancy type field to remove content after dash - vectorized
            if "occtype" in gdf.columns:
                # Convert all values to string first
                gdf["occtype"] = gdf["occtype"].astype(str)
                # Use vectorized string operations to split at first dash
                gdf["occtype"] = gdf["occtype"].str.split('-', n=1).str[0]
             
            # Pre-process the foundation type field to map numeric values to string codes
            if "found_type" in gdf.columns and "foundation_type" not in gdf.columns:
                foundation_type_map = {
                    1: "I",  # Pile
                    2: "P",  # Pier
                    3: "W",  # Solid Wall
                    4: "B",  # Basement
                    5: "C",  # Crawl
                    6: "F",  # Fill
                    7: "S",  # Slab
                }
                
                # Using pandas categories can be more memory efficient for large datasets
                gdf["foundation_type"] = pd.to_numeric(gdf["found_type"], errors='coerce') \
                                               .map(foundation_type_map) \
                                               .astype("category")

        except Exception as e:
            raise ValueError(f"Failed to load GeoPackage: {str(e)}")
        
        # Initialize the parent class with the loaded and preprocessed GeoDataFrame
        super().__init__(gdf, overrides)
