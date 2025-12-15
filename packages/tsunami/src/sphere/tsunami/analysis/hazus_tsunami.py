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
        bldg_deductible = 5_000,
        bldg_cap = 250_000,
        cont_deductible = 1_250,
        cont_cap = 100_000,
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
        self.bldg_deductible = bldg_deductible
        self.bldg_cap = bldg_cap
        self.cont_deductible = cont_deductible
        self.cont_cap = cont_cap

        with (
            resources.files("sphere.data")
            .joinpath("eqEconCapParams.csv")
            .open("r", encoding="utf-8-sig") as econ_cap_params_file
        ):
            self.econ_cap_params = pd.read_csv(econ_cap_params_file)
        
        with (
            resources.files("sphere.data")
            .joinpath("eqEconIncParams.csv")
            .open("r", encoding="utf-8-sig") as econ_inc_params_file
        ):
            self.econ_inc_params = pd.read_csv(econ_inc_params_file)
        

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

        # First assign the two values from the rasters
        # Assign depth values and bin them in 0.1 increments
        print("Calculating flood depth and flux for buildings...")
        depth_in_structure = (2.0 / 3.0 * 1250.0 / 381.0 * (self.depth_grid.get_value_vectorized(gdf.geometry))) - self.buildings.first_floor_height.to_frame().values
        self.buildings.flood_depth = depth_in_structure # np.maximum(0, np.floor(np.nan_to_num(depth_in_structure) / 0.1) * 0.1) 

        # Assign flux values and bin them in 50 increments, rounding down
        raw_flux = 2.0 / 3.0 * (1250.0 ** 3 / 381.0 ** 3) * self.momentum_flux.get_value_vectorized(gdf.geometry)
        self.buildings.flux = raw_flux # 50 * np.floor(np.nan_to_num(raw_flux) / 50)

        # Then we need to apply vulnerabilities to get the median and betas and compute damage states
        self.fragility_function.compute_damage_states(self.buildings)
        
        # For multiple columns these have to be looped because loc can only be used with a 1-dimensional boolean index
        # Operations are still vectorized (not iterating through rows)
        str_com_cols = self.buildings.fields.get_field_name('probability_str_complete')
        str_com_cols = [field for field in (str_com_cols if isinstance(str_com_cols, list) else [str_com_cols])]
        nsd_com_cols = self.buildings.fields.get_field_name('probability_nsd_complete')
        content_com_cols = self.buildings.fields.get_field_name('probability_content_complete')
        nsd_mod_cols = self.buildings.fields.get_field_name('probability_nsd_moderate')
        nsd_ext_cols = self.buildings.fields.get_field_name('probability_nsd_extensive')
        nsd_none_cols = self.buildings.fields.get_field_name('probability_nsd_none')
        content_mod_cols = self.buildings.fields.get_field_name('probability_content_moderate')
        content_ext_cols = self.buildings.fields.get_field_name('probability_content_extensive')
        content_none_cols = self.buildings.fields.get_field_name('probability_content_none')
        # Listify these if they're strings
        nsd_com_cols = [field for field in (nsd_com_cols if isinstance(nsd_com_cols, list) else [nsd_com_cols])]
        content_com_cols = [field for field in (content_com_cols if isinstance(content_com_cols, list) else [content_com_cols])]
        nsd_mod_cols = [field for field in (nsd_mod_cols if isinstance(nsd_mod_cols, list) else [nsd_mod_cols])]
        nsd_ext_cols = [field for field in (nsd_ext_cols if isinstance(nsd_ext_cols, list) else [nsd_ext_cols])]
        nsd_none_cols = [field for field in (nsd_none_cols if isinstance(nsd_none_cols, list) else [nsd_none_cols])]
        content_mod_cols = [field for field in (content_mod_cols if isinstance(content_mod_cols, list) else [content_mod_cols])]
        content_ext_cols = [field for field in (content_ext_cols if isinstance(content_ext_cols, list) else [content_ext_cols])]
        content_none_cols = [field for field in (content_none_cols if isinstance(content_none_cols, list) else [content_none_cols])]
        
        for str_com_col, nsd_com_col, content_com_col, nsd_mod_col, nsd_ext_col, nsd_none_col, content_mod_col, content_ext_col, content_none_col in zip(
            str_com_cols,
            nsd_com_cols,
            content_com_cols,
            nsd_mod_cols,
            nsd_ext_cols,
            nsd_none_cols,
            content_mod_cols,
            content_ext_cols,
            content_none_cols
        ):
            # Where the structural probability is over 70% we need to set the non-structural and contents probabilities to 100%
            # Create a condition mask for buildings with complete structural probability > 70%
            high_struct_damage_mask = gdf[str_com_col] > 0.7

            # Apply vectorized updates where the mask is True
            # Set complete probabilities to 100%
            gdf.loc[high_struct_damage_mask, nsd_com_col] = 1.0
            gdf.loc[high_struct_damage_mask, content_com_col] = 1.0

            # Set moderate and extensive probabilities to 0%
            gdf.loc[high_struct_damage_mask, nsd_mod_col] = 0.0
            gdf.loc[high_struct_damage_mask, nsd_ext_col] = 0.0
            gdf.loc[high_struct_damage_mask, nsd_none_col] = 0.0
            gdf.loc[high_struct_damage_mask, content_mod_col] = 0.0
            gdf.loc[high_struct_damage_mask, content_ext_col] = 0.0
            gdf.loc[high_struct_damage_mask, content_none_col] = 0.0

        # Need to merge with the economic parameters to get repair rates
        merged_df = pd.merge(
                pd.merge(
                gdf, # Only merge needed columns initially
                self.econ_cap_params,
                left_on=self.buildings.occupancy_type,  # Specify the column in the left DataFrame
                right_on='Occupancy',  # Specify the column in the right DataFrame
                how='left',
                suffixes=('', '_econCap') # Add suffix to avoid potential column name conflicts
            ),
            self.econ_inc_params,
            left_on=self.buildings.occupancy_type,
            right_on = 'Occupancy',
            how='left',
            suffixes=('', '_econInc')
        )

        # Compute economic losses
        # For Tsunami it uses the EQ economic capacity parameters so we need to adjust any values >= 50 to 100.
        merged_df['CmpCntRepair'] = np.where(merged_df['CmpCntRepair'] >= 50, 100, merged_df['CmpCntRepair'])

        # BldgLoss
        # Create structloss fields based on flux return periods
        flux_fields = self.buildings.fields.get_field_name('flux')
        flux_fields = [field for field in (flux_fields if isinstance(flux_fields, list) else [flux_fields])]
        import re
        structloss_fields = []
        nonstrloss_fields = []
        if len(flux_fields) > 1:
            for flux_field in flux_fields:
                match = re.search(r"(_\d*y)", flux_field)
                struct_loss_field = f"StructLoss{match.group(1)}"
                structloss_fields.append(struct_loss_field)
                nonstr_loss_field = f"NonStrLoss{match.group(1)}"
                nonstrloss_fields.append(nonstr_loss_field)
        else:
            structloss_fields = "StructLoss"
            nonstrloss_fields = "NonStrLoss"
        merged_df[structloss_fields] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModStrRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtStrRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpStrRepair'].values, axis=0).values / 100.0
        ).mul(merged_df[self.buildings.fields.get_field_name('building_cost')].values, axis=0)
        merged_df[nonstrloss_fields] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_nsd_moderate')].mul(merged_df['ModNsaRepair'].values + merged_df['ModNsdRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_nsd_extensive')].mul(merged_df['ExtNsaRepair'].values + merged_df['ExtNsdRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_nsd_complete')].mul(merged_df['CmpNsaRepair'].values + merged_df['CmpNsdRepair'].values, axis=0).values / 100.0
        ).mul(merged_df[self.buildings.fields.get_field_name('building_cost')].values, axis=0)
        merged_df[self.buildings.fields.get_field_name('building_loss')] = pd.DataFrame(merged_df[structloss_fields].values + merged_df[nonstrloss_fields].values)

        # ContentLoss
        merged_df[self.buildings.fields.get_field_name('content_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_content_moderate')].mul(merged_df['ModCntRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_content_extensive')].mul(merged_df['ExtCntRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_content_complete')].mul(merged_df['CmpCntRepair'].values, axis=0).values / 100.0
        ).mul(merged_df[self.buildings.fields.get_field_name('content_cost')].values, axis=0)
        
        # RelocLoss (broken down for clarity)
        pct_owner_occ_ratio = merged_df['PctOwnerOcc'] / 100.0
        non_owner_prob = merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].add(merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].values, axis=0).add(merged_df[self.buildings.fields.get_field_name('probability_str_complete')].values, axis=0)
        non_owner_loss = non_owner_prob.mul(merged_df['DisruptCostPerMonth'].values, axis=0).mul(1.0 - pct_owner_occ_ratio, axis=0)

        disrupt_daily = merged_df['DisruptCostPerMonth'].values / 30.0 # Assuming 30 days per month as implied
        owner_mod_loss = merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(disrupt_daily + merged_df['RentPerDay'].mul(merged_df['ModRecoveryTime'].values, axis=0).values, axis=0)
        owner_ext_loss = merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(disrupt_daily + merged_df['RentPerDay'].mul(merged_df['ExtRecoveryTime'].values, axis=0).values, axis=0)
        owner_comp_loss = merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(disrupt_daily + merged_df['RentPerDay'].mul(merged_df['CmpRecoveryTime'].values, axis=0).values, axis=0)
        owner_loss = (owner_mod_loss.add(owner_ext_loss.values, axis=0).add(owner_comp_loss.values, axis=0)).mul(pct_owner_occ_ratio.values, axis=0)
        merged_df[self.buildings.fields.get_field_name('relocation_loss')] = pd.DataFrame((non_owner_loss.add(owner_loss.values, axis=0)).mul(merged_df[self.buildings.fields.get_field_name('area')].values, axis=0))

        # IncLoss (broken down for clarity)
        merged_df[self.buildings.fields.get_field_name('income_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModRecoveryTime'].values + merged_df['ModConstrTime'].values, axis=0).values  +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtRecoveryTime'].values + merged_df['ExtConstrTime'].values, axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpRecoveryTime'].values + merged_df['CmpConstrTime'].values, axis=0).values
        ).mul(1.0 - merged_df['IncomeRecap'].values, axis=0).mul(merged_df[self.buildings.fields.get_field_name('area')].values, axis=0).mul(merged_df['IncPerDay'].values, axis=0)

        # RentLoss
        merged_df[self.buildings.fields.get_field_name('rental_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModRecoveryTime'].values, axis=0).values  +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtRecoveryTime'].values, axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpRecoveryTime'].values, axis=0).values
        ).mul((1.0 - pct_owner_occ_ratio) * merged_df[self.buildings.fields.get_field_name('area')].values * merged_df['RentPerDay'].values, axis=0)

        # WageLoss (uses the same time calculation as IncLoss)
        merged_df[self.buildings.fields.get_field_name('wage_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModRecoveryTime'].values + merged_df['ModConstrTime'].values, axis=0).values  +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtRecoveryTime'].values + merged_df['ExtConstrTime'].values, axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpRecoveryTime'].values + merged_df['CmpConstrTime'].values, axis=0).values
        ).mul((1.0 - merged_df['WageRecap'].values) * merged_df[self.buildings.fields.get_field_name('area')].values * merged_df['WagePerDay'].values, axis=0)

        # InvLoss Needs eqTractDsBt Damage state probabilities
        weighted_inv_dmg = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_content_moderate')].mul(merged_df['ModInvDmg'], axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_content_extensive')].mul(merged_df['ExtInvDmg'], axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_content_complete')].mul(merged_df['CmpInvDmg'], axis=0).values
        ) / 100.0 # Apply the division by 100 from the SQL

        inventory_value = merged_df[self.buildings.fields.get_field_name('area')] * merged_df['GrossSales'] * merged_df['BusinessInv'] / 100

        merged_df[self.buildings.fields.get_field_name('inventory_loss')] = pd.DataFrame(
            weighted_inv_dmg.mul(inventory_value.values, axis=0)
        )

        # Compute Bulding Loss AAL
        def calc_aal(losses_df):
            # Get return periods from column names using regex
            return_periods = []
            for col in losses_df.columns.values:
                # keep only the numeral
                match = re.search(r"(\d+)(y)", col)
                if match:
                    return_periods.append(int(match.group(1)))
            
            sum_ann_loss = pd.DataFrame(0.0, index=losses_df.index, columns=[return_periods])
            for p in return_periods:
                if return_periods.index(p) == len(return_periods) - 1:
                    sum_ann_loss[p] = ((1 / p) * losses_df.iloc[:, return_periods.index(p)])
                else:
                    # print(((1 / p) - (1 / return_periods[return_periods.index(p) + 1])) * ((losses_df.iloc[:, return_periods.index(p)] + losses_df.iloc[:, return_periods.index(p) + 1]) / 2).head(1))
                    sum_ann_loss[p] = ((1 / p) - (1 / return_periods[return_periods.index(p) + 1])) * ((losses_df.iloc[:, return_periods.index(p)] + losses_df.iloc[:, return_periods.index(p) + 1]) / 2)
            sum_ann_loss['SumAnnLoss'] = sum_ann_loss.loc[:].sum(axis=1)
            return sum_ann_loss['SumAnnLoss']
        
        def adjust_loss_dedlim(losses_df, ded=0, lim=1000000000):
            llosses_df = losses_df.sub(ded).clip(0, lim)
            return llosses_df
        
        if len(flux_fields) == 1:
            return merged_df

        # Compute Building Loss AAL
        merged_df[self.buildings.fields.get_field_name('building_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('building_loss')])
    
        # Compute Content Loss AAL
        merged_df[self.buildings.fields.get_field_name('content_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('content_loss')])

        # Compute Relocation Loss AAL
        merged_df[self.buildings.fields.get_field_name('relocation_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('relocation_loss')])

        # Compute Income Loss AAL
        merged_df[self.buildings.fields.get_field_name('income_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('income_loss')])

        # Compute Rental Loss AAL
        merged_df[self.buildings.fields.get_field_name('rental_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('rental_loss')])

        # Compute Wage Loss AAL
        merged_df[self.buildings.fields.get_field_name('wage_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('wage_loss')])

        # Compute Inventory Loss AAL
        merged_df[self.buildings.fields.get_field_name('inventory_loss_aal')] = calc_aal(merged_df[self.buildings.fields.get_field_name('inventory_loss')])

        # Compute Building Loss AAL with deductible
        merged_df[self.buildings.fields.get_field_name('gross_building_loss_aal')] = calc_aal(
            adjust_loss_dedlim(
                merged_df[self.buildings.fields.get_field_name('building_loss')],
                self.bldg_deductible,
                self.bldg_cap,
            )
        )

        # Compute Content Loss AAL with deductible
        merged_df[self.buildings.fields.get_field_name('gross_content_loss_aal')] = calc_aal(
            adjust_loss_dedlim(
                merged_df[self.buildings.fields.get_field_name('content_loss')],
                self.cont_deductible,
                self.cont_cap,
            )
        )

        
        return merged_df