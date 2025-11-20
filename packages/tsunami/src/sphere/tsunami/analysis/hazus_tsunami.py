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


class HazusTsunamiAnalysis:    
    def __init__(
        self,
        buildings: Buildings,
        vulnerability_func: AbstractVulnerabilityFunction,
        depth_grid: AbstractRasterReader,
        momentum_flux: AbstractRasterReader,
    ):
        """
        Initializes a HazusFloodAnalysis object.

        Args:
            buildings (BuildingPoints): BuildingPoints object.
            vulnerability_func (VulnerabilityFunction): VulnerabilityFunction object.
            hazard (Hazard): Hazard object.
        """
        self.buildings = buildings
        self.fragility_function = vulnerability_func
        self.depth_grid = depth_grid
        self.momentum_flux = momentum_flux

        with (
            resources.files("sphere.data")
            .joinpath("eqEconCapParams.csv")
            .open("r", encoding="utf-8-sig") as economic_params_file
        ):
            self.economic_params = pd.read_csv(economic_params_file)
        

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

        # TODO: Change out the buildings.fields to be the property access instead.
        
        gdf: gpd.GeoDataFrame = self.buildings.gdf
        fields = self.buildings.fields

        # First assign the two values from the rasters
        # Assign depth values and bin them in 0.1 increments
        depth_in_structure = (2.0 / 3.0 * 1250.0 / 381.0 * (self.depth_grid.get_value_vectorized(gdf.geometry))) - gdf[self.buildings.fields.first_floor_height]
        gdf[self.buildings.fields.flood_depth] = depth_in_structure # np.maximum(0, np.floor(np.nan_to_num(depth_in_structure) / 0.1) * 0.1) 

        # Assign flux values and bin them in 50 increments, rounding down
        raw_flux = 2.0 / 3.0 * (1250.0 ** 3 / 381.0 ** 3) * self.momentum_flux.get_value_vectorized(gdf.geometry)
        gdf[self.buildings.fields.flux] = raw_flux # 50 * np.floor(np.nan_to_num(raw_flux) / 50)

        # Then we need to apply vulnerabilities to get the median and betas and compute damage states
        self.fragility_function.compute_damage_states(self.buildings)

        # Where the structural probability is over 70% we need to set the non-structural and contents probabilities to 100%
        # Create a condition mask for buildings with complete structural probability > 70%
        high_struct_damage_mask = gdf[self.buildings.fields.probability_str_complete] > 0.7

        # Apply vectorized updates where the mask is True
        # Set complete probabilities to 100%
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_nsd_complete] = 1.0
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_content_complete] = 1.0

        # Set moderate and extensive probabilities to 0%
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_nsd_moderate] = 0.0
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_nsd_extensive] = 0.0
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_nsd_none] = 0.0
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_content_moderate] = 0.0
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_content_extensive] = 0.0
        gdf.loc[high_struct_damage_mask, self.buildings.fields.probability_content_none] = 0.0

        # Need to merge with the economic parameters to get repair rates
        merged_df = pd.merge(
            gdf, # Only merge needed columns initially
            self.economic_params,
            left_on=self.buildings.fields.occupancy_type,  # Specify the column in the left DataFrame
            right_on='Occupancy',  # Specify the column in the right DataFrame
            how='left',
            suffixes=('', '_frag') # Add suffix to avoid potential column name conflicts
        )

        # Compute economic losses
        # For Tsunami it uses the EQ economic capacity parameters so we need to adjust any values >= 50 to 100.
        merged_df['CmpCntRepair'] = np.where(merged_df['CmpCntRepair'] >= 50, 100, merged_df['CmpCntRepair'])

        # BldgLoss
        merged_df['StructLoss'] = (merged_df[self.buildings.fields.building_cost] * (
            merged_df[self.buildings.fields.probability_str_moderate] * merged_df['ModStrRepair'] / 100.0 +
            merged_df[self.buildings.fields.probability_str_extensive] * merged_df['ExtStrRepair'] / 100.0 +
            merged_df[self.buildings.fields.probability_str_complete] * merged_df['CmpStrRepair'] / 100.0
        )) 
        merged_df['NonStrLoss'] = (merged_df[self.buildings.fields.building_cost] * (
            merged_df[self.buildings.fields.probability_nsd_moderate] * (merged_df['ModNsaRepair'] + merged_df['ModNsdRepair']) / 100.0 +
            merged_df[self.buildings.fields.probability_nsd_extensive] * (merged_df['ExtNsaRepair'] + merged_df['ExtNsdRepair']) / 100.0 +
            merged_df[self.buildings.fields.probability_nsd_complete] * (merged_df['CmpNsaRepair'] + merged_df['CmpNsdRepair']) / 100.0
        ))
        merged_df[self.buildings.fields.building_loss] = merged_df['StructLoss'] + merged_df['NonStrLoss']

        # ContentLoss
        merged_df[self.buildings.fields.content_loss] = (merged_df[self.buildings.fields.content_cost] * (
            merged_df[self.buildings.fields.probability_content_moderate] * merged_df['ModCntRepair'] / 100.0 +
            merged_df[self.buildings.fields.probability_content_extensive] * merged_df['ExtCntRepair'] / 100.0 +
            merged_df[self.buildings.fields.probability_content_complete] * merged_df['CmpCntRepair'] / 100.0
        ))
        
        # RelocLoss (broken down for clarity)
        pct_owner_occ_ratio = merged_df['PctOwnerOcc'] / 100.0
        non_owner_prob = merged_df[self.buildings.fields.probability_str_moderate] + merged_df[self.buildings.fields.probability_str_extensive] + merged_df[self.buildings.fields.probability_str_complete]
        non_owner_loss = (1.0 - pct_owner_occ_ratio) * non_owner_prob * merged_df['DisruptCostPerMonth']

        disrupt_daily = merged_df['DisruptCostPerMonth'] / 30.0 # Assuming 30 days per month as implied
        owner_mod_loss = merged_df[self.buildings.fields.probability_str_moderate] * (disrupt_daily + merged_df['RentPerDay'] * merged_df['ModRecoveryTime'])
        owner_ext_loss = merged_df[self.buildings.fields.probability_str_extensive] * (disrupt_daily + merged_df['RentPerDay'] * merged_df['ExtRecoveryTime'])
        owner_comp_loss = merged_df[self.buildings.fields.probability_str_complete] * (disrupt_daily + merged_df['RentPerDay'] * merged_df['CmpRecoveryTime'])
        owner_loss = pct_owner_occ_ratio * (owner_mod_loss + owner_ext_loss + owner_comp_loss)

        merged_df[self.buildings.fields.relocation_loss] = merged_df[self.buildings.fields.area] * (non_owner_loss + owner_loss)

        # IncLoss (broken down for clarity)
        merged_df[self.buildings.fields.income_loss] = (1.0 - merged_df['IncomeRecap']) * merged_df[self.buildings.fields.area] * merged_df['IncPerDay'] * (
            merged_df[self.buildings.fields.probability_str_moderate] * (merged_df['ModRecoveryTime'] + merged_df['ModConstrTime'])  +
            merged_df[self.buildings.fields.probability_str_extensive] * (merged_df['ExtRecoveryTime'] + merged_df['ExtConstrTime']) +
            merged_df[self.buildings.fields.probability_str_complete] * (merged_df['CmpRecoveryTime'] + merged_df['CmpConstrTime'])
        )

        # RentLoss
        merged_df[self.buildings.fields.rental_loss] = (1.0 - pct_owner_occ_ratio) * merged_df[self.buildings.fields.area] * merged_df['RentPerDay'] * (
            (merged_df[self.buildings.fields.probability_str_moderate] * merged_df['ModRecoveryTime'])  +
            (merged_df[self.buildings.fields.probability_str_extensive] * merged_df['ExtRecoveryTime']) +
            (merged_df[self.buildings.fields.probability_str_complete] * merged_df['CmpRecoveryTime'])
        )

        # WageLoss (uses the same time calculation as IncLoss)
        merged_df[self.buildings.fields.wage_loss] = (1.0 - merged_df['WageRecap']) * merged_df[self.buildings.fields.area] * merged_df['WagePerDay'] * (
            merged_df[self.buildings.fields.probability_str_moderate] * (merged_df['ModRecoveryTime'] + merged_df['ModConstrTime'])  +
            merged_df[self.buildings.fields.probability_str_extensive] * (merged_df['ExtRecoveryTime'] + merged_df['ExtConstrTime']) +
            merged_df[self.buildings.fields.probability_str_complete] * (merged_df['CmpRecoveryTime'] + merged_df['CmpConstrTime'])
        )

        # InvLoss Needs eqTractDsBt Damage state probabilities
        """ weighted_inv_dmg = (
            gdf['PModDmg'] * gdf['ModInvDmg'] +
            gdf['PExtDmg'] * gdf['ExtInvDmg'] +
            gdf['PCompDmg'] * gdf['CmpInvDmg']
        ) / 100.0 # Apply the division by 100 from the SQL

        merged_df[self.buildings.fields.inventory_loss] = merged_df[self.buildings.fields.area] * gdf['GrossSales'] * 1000.0 * (gdf['BusinessInv'] / 100.0) * (
            merged_df[self.buildings.fields.probability_str_moderate] * (merged_df['ModInvDmg'] / 100.0)    
        ) """


        return merged_df