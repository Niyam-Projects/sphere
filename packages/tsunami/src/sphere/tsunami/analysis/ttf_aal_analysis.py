import logging
# logger = logging.getLogger(__name__)
import numpy as np
import pandas as pd
import geopandas as gpd
import os
from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction
import warnings
# Pandas performance warnings are largely unnecessary and are generated even if the performance is acceptable.
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

try:
    # Python 3.9+
    import importlib.resources as resources
except ImportError:
    # For earlier versions, install importlib_resources
    import importlib_resources as resources


class ttfAALAnalysis:    
    def __init__(
        self,
        buildings: Buildings,
        vulnerability_func: AbstractVulnerabilityFunction,
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
        flux_cols = self.buildings.fields.get_field_name('flux')
        return_periods = flux_cols if isinstance(flux_cols, list) else [flux_cols]
        logging.info(
            f"Starting TTF tsunami loss calculation for {len(gdf)} buildings "
            f"across {len(return_periods)} return period(s): {return_periods}"
        )

        # Compute depth in structure (flood_depth - first_floor_height) for NSD and content damage
        # Clamp to 0 minimum - negative values mean water doesn't reach structure (no damage)
        flood_depth_cols = self.buildings.fields.get_field_name('flood_depth')
        ffh_field = self.buildings.fields.get_field_name('first_floor_height')
        self.buildings.depth_in_structure = gdf[flood_depth_cols].sub(gdf[ffh_field], axis=0).clip(lower=0)

        # Plausibility check — warn if all flux values are zero
        flux_vals = gdf[return_periods].values.ravel()
        if np.all(flux_vals[~np.isnan(flux_vals)] == 0):
            logging.warning("All momentum flux values are zero. Verify the correct input columns were provided.")

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
                left_on=self.buildings.fields.get_field_name("occupancy_type"),  # Specify the column in the left DataFrame
                right_on='Occupancy',  # Specify the column in the right DataFrame
                how='left',
                suffixes=('', '_econCap') # Add suffix to avoid potential column name conflicts
            ),
            self.econ_inc_params,
            left_on=self.buildings.fields.get_field_name("occupancy_type"),
            right_on = 'Occupancy',
            how='left',
            suffixes=('', '_econInc')
        )

        # Compute economic losses
        # For Tsunami it uses the EQ economic capacity parameters so we need to adjust any values >= 50 to 100.
        merged_df['CmpCntRepair'] = np.where(merged_df['CmpCntRepair'] >= 50, 100, merged_df['CmpCntRepair'])

        # Uncomment line below to use 100% CmpInvDmg if needed
        # merged_df['CmpInvDmg'] = np.where(merged_df['CmpInvDmg'] >= 50, 100, merged_df['CmpInvDmg'])

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
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpStrRepair'].values, axis=0).values / 100.0,
            dtype=float
        ).mul(merged_df[self.buildings.fields.get_field_name('building_cost')].values, axis=0)
        merged_df[nonstrloss_fields] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_nsd_moderate')].mul(merged_df['ModNsaRepair'].values + merged_df['ModNsdRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_nsd_extensive')].mul(merged_df['ExtNsaRepair'].values + merged_df['ExtNsdRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_nsd_complete')].mul(merged_df['CmpNsaRepair'].values + merged_df['CmpNsdRepair'].values, axis=0).values / 100.0,
            dtype=float
        ).mul(merged_df[self.buildings.fields.get_field_name('building_cost')].values, axis=0)
        merged_df[self.buildings.fields.get_field_name('building_loss')] = pd.DataFrame(merged_df[structloss_fields].values + merged_df[nonstrloss_fields].values)

        # ContentLoss
        merged_df[self.buildings.fields.get_field_name('content_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_content_moderate')].mul(merged_df['ModCntRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_content_extensive')].mul(merged_df['ExtCntRepair'].values, axis=0).values / 100.0 +
            merged_df[self.buildings.fields.get_field_name('probability_content_complete')].mul(merged_df['CmpCntRepair'].values, axis=0).values / 100.0,
            dtype=float
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
        merged_df[self.buildings.fields.get_field_name('relocation_loss')] = pd.DataFrame((non_owner_loss.add(owner_loss.values, axis=0)).mul(merged_df[self.buildings.fields.get_field_name('area')].values, axis=0), dtype=float)

        # IncLoss (broken down for clarity)
        merged_df[self.buildings.fields.get_field_name('income_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModRecoveryTime'].values + merged_df['ModConstrTime'].values, axis=0).values  +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtRecoveryTime'].values + merged_df['ExtConstrTime'].values, axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpRecoveryTime'].values + merged_df['CmpConstrTime'].values, axis=0).values,
            dtype=float
        ).mul(1.0 - merged_df['IncomeRecap'].values, axis=0).mul(merged_df[self.buildings.fields.get_field_name('area')].values, axis=0).mul(merged_df['IncPerDay'].values, axis=0)

        # RentLoss
        merged_df[self.buildings.fields.get_field_name('rental_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModRecoveryTime'].values, axis=0).values  +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtRecoveryTime'].values, axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpRecoveryTime'].values, axis=0).values,
            dtype=float
        ).mul((1.0 - pct_owner_occ_ratio) * merged_df[self.buildings.fields.get_field_name('area')].values * merged_df['RentPerDay'].values, axis=0)

        # WageLoss (uses the same time calculation as IncLoss)
        merged_df[self.buildings.fields.get_field_name('wage_loss')] = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_str_moderate')].mul(merged_df['ModRecoveryTime'].values + merged_df['ModConstrTime'].values, axis=0).values  +
            merged_df[self.buildings.fields.get_field_name('probability_str_extensive')].mul(merged_df['ExtRecoveryTime'].values + merged_df['ExtConstrTime'].values, axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_str_complete')].mul(merged_df['CmpRecoveryTime'].values + merged_df['CmpConstrTime'].values, axis=0).values,
            dtype=float
        ).mul((1.0 - merged_df['WageRecap'].values) * merged_df[self.buildings.fields.get_field_name('area')].values * merged_df['WagePerDay'].values, axis=0)

        # InvLoss Needs eqTractDsBt Damage state probabilities
        weighted_inv_dmg = pd.DataFrame(
            merged_df[self.buildings.fields.get_field_name('probability_nsd_moderate')].mul(merged_df['ModInvDmg'], axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_nsd_extensive')].mul(merged_df['ExtInvDmg'], axis=0).values +
            merged_df[self.buildings.fields.get_field_name('probability_nsd_complete')].mul(merged_df['CmpInvDmg'], axis=0).values,
            dtype=float
        ) / 100.0 # Apply the division by 100 from the SQL

        inventory_value = merged_df[self.buildings.fields.get_field_name('area')] * merged_df['GrossSales'] * merged_df['BusinessInv'] / 100

        merged_df[self.buildings.fields.get_field_name('inventory_loss')] = pd.DataFrame(
            weighted_inv_dmg.mul(inventory_value.values, axis=0),
            dtype=float
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
            
            sum_ann_loss = pd.DataFrame(0.0, index=losses_df.index, columns=[return_periods], dtype=float)
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
    
        # Compute BldgAAL_lossratio_USDperM
        merged_df[self.buildings.fields.get_field_name('BldgAAL_LossRatio_USDperM')] = (
            merged_df[self.buildings.fields.get_field_name('building_loss_aal')] / ( merged_df[self.buildings.fields.get_field_name('building_cost')] / 1_000_000 )
        )

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

        # Compute Gross Building Losses
        merged_df[self.buildings.fields.get_field_name('gross_building_loss')] = adjust_loss_dedlim(
            merged_df[self.buildings.fields.get_field_name('building_loss')],
            self.bldg_deductible,
            self.bldg_cap,
        )
        
        # Compute Gross Content Losses
        merged_df[self.buildings.fields.get_field_name('gross_content_loss')] = adjust_loss_dedlim(
            merged_df[self.buildings.fields.get_field_name('content_loss')],
            self.cont_deductible,
            self.cont_cap,
        )
        
        # Compute Building Loss AAL with deductible
        merged_df[self.buildings.fields.get_field_name('gross_building_loss_aal')] = calc_aal(
            # adjust_loss_dedlim(
            #     merged_df[self.buildings.fields.get_field_name('building_loss')],
            #     self.bldg_deductible,
            #     self.bldg_cap,
            # )
            merged_df[self.buildings.fields.get_field_name('gross_building_loss')]
        )
        
        # Compute GrossBldgAAL_lossratio_USDperM
        merged_df[self.buildings.fields.get_field_name('GrossBldgAAL_LossRatio_USDperM')] = (
            merged_df[self.buildings.fields.get_field_name('gross_building_loss_aal')] / ( merged_df[self.buildings.fields.get_field_name('building_cost')] / 1_000_000 )
        )

        # Compute Content Loss AAL with deductible
        merged_df[self.buildings.fields.get_field_name('gross_content_loss_aal')] = calc_aal(
            # adjust_loss_dedlim(
            #     merged_df[self.buildings.fields.get_field_name('content_loss')],
            #     self.cont_deductible,
            #     self.cont_cap,
            # )
            merged_df[self.buildings.fields.get_field_name('gross_content_loss')]
        )

        # Compute Capital Loss AAL (building + content + inventory)
        merged_df[self.buildings.fields.get_field_name('CapitalLoss_AAL')] = (
            merged_df[self.buildings.fields.get_field_name('building_loss_aal')]
                .add(merged_df[self.buildings.fields.get_field_name('content_loss_aal')].values)
                .add(merged_df[self.buildings.fields.get_field_name('inventory_loss_aal')].values)
        )

        # Compute Income Loss AAL (relocation, income, rental, wage)
        merged_df[self.buildings.fields.get_field_name('IncomeLoss_AAL')] = (
            merged_df[self.buildings.fields.get_field_name('relocation_loss_aal')]
                .add(merged_df[self.buildings.fields.get_field_name('income_loss_aal')].values)
                .add(merged_df[self.buildings.fields.get_field_name('rental_loss_aal')].values)
                .add(merged_df[self.buildings.fields.get_field_name('wage_loss_aal')].values)
        )

        # Compute Total Economic Loss AAL (capital + income)
        merged_df[self.buildings.fields.get_field_name('TotalEconomicLoss_AAL')] = (
            merged_df[self.buildings.fields.get_field_name('CapitalLoss_AAL')]
                .add(merged_df[self.buildings.fields.get_field_name('IncomeLoss_AAL')].values)
        )


        # Ensure proper field order

        column_order = [

        ]

        def reorder_columns(df, column_order):
            """
            Reorders DataFrame columns to match a specified order.
            - Skips columns in the list that don't exist in the DataFrame
            - Supports wildcard patterns using '*' (e.g., 'FlowDepth_*yr_Median_ft')
            - Any DataFrame columns not matched by the list are dropped
            """
            matched_columns = []
            
            for col in column_order:
                if '*' in col:
                    # Convert wildcard pattern to regex
                    pattern = re.compile('^' + re.escape(col).replace(r'\*', '.*') + '$')
                    matches = [c for c in df.columns if pattern.match(c)]
                    matched_columns.extend(matches)
                elif col in df.columns:
                    matched_columns.append(col)
                # If col not in df, silently skip it
            
            return df[matched_columns]

        return merged_df