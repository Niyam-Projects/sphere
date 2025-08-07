import os
from typing import Dict, List
import geopandas as gpd
import pandas as pd
from sphere.core.schemas.buildings import Buildings

class FastBuildings(Buildings):
    """
    Fast buildings class for loading CSV files with automatic coordinate column detection.
    """
    
    def __init__(self, csv_file: str, overrides: Dict[str, str] | None = None):
        # Default field mappings
        default_overrides = {
            "id": "FltyId",
            "occupancy_type": "Occ",
            "first_floor_height": "FirstFloorHt",
            "foundation_type": "FoundationType",
            "number_stories": "NumStories",
            "area": "Area",
            "building_cost": "Cost",
            "content_cost": "ContentCost",
            "inventory_cost": "InventoryCostUSD",
            "flood_depth": "FloodDepth",
            "depth_in_structure": "DepthInStructure",
            "bddf_id": "BldgDamageFnID",
            "building_damage_percent": "BldgDmgPct",
            "building_loss": "BldgLossUSD",
            "cddf_id": "CDDF_ID",
            "content_damage_percent": "ContDmgPct",
            "content_loss": "ContentLossUSD",
            "iddf_id": "IDDF_ID",
            "inventory_damage_percent": "InvDmgPct",
            "inventory_loss": "InventoryLossUSD",
            "debris_finish": "DebrisFinish",
            "debris_foundation": "DebrisFoundation",
            "debris_structure": "DebrisStructure",
            "debris_total": "DebrisTotal",
        }
        
        # Merge with user overrides if provided
        if overrides:
            default_overrides.update(overrides)

        # If csv_file does not have a drive letter, assume relative to cwd.
        drive, _ = os.path.splitdrive(csv_file)
        if not drive:
            csv_path = os.path.join(os.getcwd(), csv_file)
        else:
            csv_path = csv_file

        try:
            # Load the CSV file
            df = pd.read_csv(csv_path)
            
            # Find longitude and latitude columns
            lon_col, lat_col = self._find_coordinate_columns(df.columns.tolist())
            
            # Create GeoDataFrame from x,y coordinates
            gdf = gpd.GeoDataFrame(
                df, 
                geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), 
                crs="EPSG:4326"
            )
            
        except Exception as e:
            raise ValueError(f"Failed to load CSV file: {str(e)}")
        
        # Initialize the parent class with the loaded GeoDataFrame
        super().__init__(gdf, default_overrides)
    
    def _find_coordinate_columns(self, columns: List[str]) -> tuple[str, str]:
        """
        Find longitude and latitude columns using case-insensitive matching.
        
        Args:
            columns: List of column names from the DataFrame
            
        Returns:
            Tuple of (longitude_column, latitude_column)
            
        Raises:
            ValueError: If coordinate columns cannot be found
        """
        # Possible longitude column names
        lon_candidates = ["longitude", "x", "lon", "lng"]
        # Possible latitude column names  
        lat_candidates = ["latitude", "y", "lat"]
        
        # Convert columns to lowercase for case-insensitive matching
        columns_lower = {col.lower(): col for col in columns}
        
        # Find longitude column
        lon_col = None
        for candidate in lon_candidates:
            if candidate in columns_lower:
                lon_col = columns_lower[candidate]
                break
        
        # Find latitude column
        lat_col = None
        for candidate in lat_candidates:
            if candidate in columns_lower:
                lat_col = columns_lower[candidate]
                break
        
        if lon_col is None:
            raise ValueError(f"Could not find longitude column. Looked for: {lon_candidates}")
        if lat_col is None:
            raise ValueError(f"Could not find latitude column. Looked for: {lat_candidates}")
            
        return lon_col, lat_col
