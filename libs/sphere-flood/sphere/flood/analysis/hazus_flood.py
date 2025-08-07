import numpy as np
import pandas as pd
import geopandas as gpd
from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader

try:
    # Python 3.9+
    import importlib.resources as resources
except ImportError:
    # For earlier versions, install importlib_resources
    import importlib_resources as resources


class HazusFloodAnalysis:    
    def __init__(
        self,
        buildings: Buildings,
        vulnerability_func: AbstractVulnerabilityFunction,
        depth_grid: AbstractRasterReader,
    ):
        """
        Initializes a HazusFloodAnalysis object.

        Args:
            buildings (BuildingPoints): BuildingPoints object.
            vulnerability_func (VulnerabilityFunction): VulnerabilityFunction object.
            hazard (Hazard): Hazard object.
        """
        self.buildings: Buildings = buildings
        self.vulnerability_func = vulnerability_func
        self.depth_grid = depth_grid

        with (
            resources.files("sphere.data")
            .joinpath("flDebris.csv")
            .open("r", encoding="utf-8-sig") as debris_file
        ):
            debris_df = pd.read_csv(debris_file)
            self.debris = self._index_debris_lookup(debris_df)
        with (
            resources.files("sphere.data")
            .joinpath("flRsFnGBS.csv")
            .open("r", encoding="utf-8-sig") as restoration_file
        ):
            restoration_df = pd.read_csv(restoration_file)
            self.restoration = self._index_restoration_lookup(restoration_df)

    def calculate_losses(self):
        """
        Calculates risk for each building.

        Returns:
            pandas.DataFrame or geopandas.GeoDataFrame: Building data with risk metrics.
        """
        # Required fields according to FAST
        # Area
        # Building Cost
        # (Content Cost can be computed if not provided)
        # First floor height
        # Foundation Type (according to Hazus but is basically around basement or no)
        # Lat, Lon, Point geometry
        # Number of stories
        # Occupancy class

        gdf: gpd.GeoDataFrame = self.buildings.gdf

        # Apply the depth grid to the buildings
        self.buildings.flood_depth = self.depth_grid.get_value_vectorized(gdf.geometry)

        # From the flooded depth based on other attributes determine the depth in structure.
        self.buildings.depth_in_structure = (
            self.buildings.flood_depth - self.buildings.first_floor_height
        )

        # Lookup damage function ids
        self.vulnerability_func.calculate_vulnerability()

        # Do the loss calculations
        self.buildings.building_loss = (
            self.buildings.building_damage_percent / 100.0 * self.buildings.building_cost
        )
        self.buildings.content_loss = (
            self.buildings.content_damage_percent / 100.0 * self.buildings.content_cost
        )

        # Using an inline conditional to get a column or supply a default Series:
        inventory_cost_series = (
            self.buildings.inventory_cost
            if self.buildings.fields.get_field_name("inventory_cost") in gdf.columns
            else pd.Series(0, index=gdf.index)
        )

        if self.buildings.fields.get_field_name("inventory_damage_percent") in gdf.columns:
            self.buildings.inventory_loss = (
                self.buildings.inventory_damage_percent / 100.0 * inventory_cost_series
            )

        
        # Debris
        self._vectorized_debris_calculation()
        
        # Restoration
        self._vectorized_restoration_calculation()

    def _index_debris_lookup(self, lookup_df: pd.DataFrame) -> pd.DataFrame:
        """
        Index the debris lookup table for fast access.
        """
        # 1. Create the combined key.
        lookup_df['merge_key'] = lookup_df['SOccup'] + '_' + lookup_df['FoundType']

        # 2. Create the Interval column using the minimum and maximum flood depths.
        lookup_df['Interval'] = lookup_df.apply(
            lambda row: pd.Interval(row['MinFloodDepth'], row['MaxFloodDepth'], closed='left'),
            axis=1
        )

        # Set 'MinFloodDepth' as a temporary index to help with grouping.
        lookup_df = lookup_df.set_index('MinFloodDepth')

        # 3. Group by the combined key and create a nested index.
        lookup_df = lookup_df.groupby('merge_key')[['Interval', 'FinishWt', 'StructureWt', 'FoundationWt']].apply(
            lambda x: x.set_index('Interval')
        )
        # Reset index so that we can create an IntervalIndex column.
        lookup_df = lookup_df.reset_index()
        lookup_df['IntervalIndex'] = pd.IntervalIndex(lookup_df['Interval'])
        lookup_df = lookup_df.set_index('merge_key')

        # Expand intervals to numeric columns for vector matching.
        lookup_df['interval_left'] = lookup_df['Interval'].apply(lambda x: x.left)
        lookup_df['interval_right'] = lookup_df['Interval'].apply(lambda x: x.right)

        return lookup_df

    def _index_restoration_lookup(self, lookup_df: pd.DataFrame) -> pd.DataFrame:
        # 1. Create the Interval column using the minimum and maximum flood depths.
        lookup_df['Interval'] = lookup_df.apply(
            lambda row: pd.Interval(row['Min_Depth'], row['Max_Depth'], closed='left'),
            axis=1
        )

        # Set 'MinDepth' as a temporary index to help with grouping.
        lookup_df = lookup_df.set_index('Min_Depth')

        # 2. Group by 'SOccup' and create a nested index of intervals.
        lookup_df = lookup_df.groupby('SOccup')[['Interval', 'Min_Restor_Days', 'Max_Restor_Days']].apply(
            lambda x: x.set_index('Interval')
        )
        lookup_df = lookup_df.reset_index()

        # 3. Create an IntervalIndex and set 'SOccup' as the main grouping index.
        lookup_df['IntervalIndex'] = pd.IntervalIndex(lookup_df['Interval'])
        lookup_df = lookup_df.set_index('SOccup')

        # Expand intervals to numeric columns for vector matching.
        lookup_df['interval_left'] = lookup_df['Interval'].apply(lambda x: x.left)
        lookup_df['interval_right'] = lookup_df['Interval'].apply(lambda x: x.right)

        return lookup_df

    def _vectorized_debris_calculation(self):
        # Get building GeoDataFrame and the fields reference.
        gdf = self.buildings.gdf
        fields = self.buildings.fields

        # Work on a copy of the debris lookup DataFrame.
        debris_lookup_df = self.debris

        # Map building foundation types (in-place update) based on your provided logic.
        gdf['FoundType'] = self.buildings.foundation_type.map(
            lambda x: 'Slab' if x in (6, 7) else ('Footing' if 1 <= x <= 5 else None)
        )

        # Create the lookup key in the buildings dataframe
        gdf['merge_key'] = self.buildings.occupancy_type + '_' + gdf['FoundType']

        # Ensure columns exist for newly assigned weights
        for col in ['FinishWt', 'StructureWt', 'FoundationWt']:
            if col not in gdf.columns:
                gdf[col] = np.nan

        # Prepare a column for depth offset
        gdf['depth_offset'] = np.nan

        # For efficiency, group the debris table by merge_key and build numeric boundaries to perform fast interval lookups.
        grouped_lookup = dict(tuple(debris_lookup_df.groupby('merge_key')))

        # Process each key once
        unique_keys = gdf['merge_key'].dropna().unique()
        for key in unique_keys:
            if key not in grouped_lookup:
                continue

            sub_lookup = grouped_lookup[key]
            # Sorted arrays of interval boundaries
            starts = sub_lookup['interval_left'].values
            ends = sub_lookup['interval_right'].values

            # Select relevant buildings
            mask = gdf['merge_key'] == key
            depths = gdf.loc[mask, self.buildings.fields.get_field_name("depth_in_structure")].values

            # Use searchsorted to find the appropriate interval index for each depth
            # We look for the interval such that interval_left <= depth < interval_right
            idx = np.searchsorted(starts, depths, side='right') - 1  # Potential match
            
            # Build arrays to hold results
            finish_wts = np.full_like(depths, np.nan, dtype=float)
            structure_wts = np.full_like(depths, np.nan, dtype=float)
            foundation_wts = np.full_like(depths, np.nan, dtype=float)
            depth_offsets = np.full_like(depths, np.nan, dtype=float)

            valid = (idx >= 0) & (idx < len(starts)) & (depths >= starts[idx]) & (depths < ends[idx])
            valid_idx = idx[valid]

            # Grab matching weights
            finish_wts[valid] = sub_lookup['FinishWt'].values[valid_idx]
            structure_wts[valid] = sub_lookup['StructureWt'].values[valid_idx]
            foundation_wts[valid] = sub_lookup['FoundationWt'].values[valid_idx]
            depth_offsets[valid] = depths[valid] - starts[valid_idx]

            # Assign results back
            gdf.loc[mask, 'FinishWt'] = finish_wts
            gdf.loc[mask, 'StructureWt'] = structure_wts
            gdf.loc[mask, 'FoundationWt'] = foundation_wts
            gdf.loc[mask, 'depth_offset'] = depth_offsets

        # Clean up and compute debris columns
        gdf.drop(columns=['FoundType', 'merge_key'], inplace=True)
        self.buildings.debris_finish = self.buildings.area * gdf["FinishWt"] / 1000
        self.buildings.debris_foundation = self.buildings.area * gdf["FoundationWt"] / 1000
        self.buildings.debris_structure = self.buildings.area * gdf["StructureWt"] / 1000
        self.buildings.debris_total = (
            self.buildings.debris_finish
            + self.buildings.debris_foundation
            + self.buildings.debris_structure
        )

    def _vectorized_restoration_calculation(self):
        """
        Vectorized restoration calculation using np.searchsorted for interval matching.
        Matches based on building occupancy_type and depth_in_structure.
        """
        gdf = self.buildings.gdf
        fields = self.buildings.fields
        restor_df = self.restoration

        # Group the restoration lookup for interval matching
        grouped_lookup = dict(tuple(restor_df.groupby('SOccup')))
        unique_keys = self.buildings.occupancy_type.dropna().unique()

        for key in unique_keys:
            if key not in grouped_lookup:
                continue

            sub_restor = grouped_lookup[key]
            starts = sub_restor['interval_left'].values
            ends = sub_restor['interval_right'].values
            mask = self.buildings.occupancy_type == key
            depths = gdf.loc[mask, self.buildings.fields.get_field_name("depth_in_structure")].values

            # Index of the correct interval
            idx = np.searchsorted(starts, depths, side='right') - 1

            min_days_vec = np.full_like(depths, np.nan, dtype=float)
            max_days_vec = np.full_like(depths, np.nan, dtype=float)

            valid = (idx >= 0) & (idx < len(starts)) & (depths >= starts[idx]) & (depths < ends[idx])
            valid_idx = idx[valid]

            min_days_vec[valid] = sub_restor['Min_Restor_Days'].values[valid_idx]
            max_days_vec[valid] = sub_restor['Max_Restor_Days'].values[valid_idx]

            gdf.loc[mask, self.buildings.fields.get_field_name("restoration_minimum")] = min_days_vec
            gdf.loc[mask, self.buildings.fields.get_field_name("restoration_maximum")] = max_days_vec
