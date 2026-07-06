import logging
logger = logging.getLogger(__name__)
import re
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
        units: str = "imperial",
    ):
        """
        Initializes a HazusFloodAnalysis object.

        Args:
            buildings (BuildingPoints): BuildingPoints object.
            vulnerability_func (VulnerabilityFunction): VulnerabilityFunction object.
            hazard (Hazard): Hazard object.
        Raises:
            NotImplementedError: If units is not "imperial".
        """
        if units != "imperial":
            raise NotImplementedError(
                f"units='{units}' is not supported. "
                "Only imperial units (feet for depth, ft³/s² for momentum flux) are currently supported."
            )
        else:
            logger.info(f"Using imperial units for TTF tsunami analysis.")
        self.units = units
        self.buildings = buildings
        self.fragility_function = vulnerability_func

        # Validate MomFlux / FlowDepth columns (ttfBuildings only)
        flux_list = getattr(buildings, 'flux_return_list', None)
        depth_list = getattr(buildings, 'flood_return_list', None)
        if flux_list is not None and depth_list is not None:
            _errs = []
            if len(flux_list) == 0:
                _errs.append(
                    "No MomFlux columns found in input DataFrame. "
                    "Expected columns starting with 'MomFlux' (e.g. MomFlux_100yr_Median_ft_per_sec)."
                )
            if len(depth_list) == 0:
                _errs.append(
                    "No FlowDepth columns found in input DataFrame. "
                    "Expected columns starting with 'FlowDepth' (e.g. FlowDepth_100yr_Median_ft)."
                )
            if not _errs:
                _flux_periods = [re.search(r'(\d+)yr', c, re.IGNORECASE).group(1) for c in flux_list]
                _depth_periods = [re.search(r'(\d+)yr', c, re.IGNORECASE).group(1) for c in depth_list]
                if len(set(_flux_periods)) != len(flux_list):
                    _errs.append(f"Duplicate return periods detected in MomFlux columns: {flux_list}")
                if len(set(_depth_periods)) != len(depth_list):
                    _errs.append(f"Duplicate return periods detected in FlowDepth columns: {depth_list}")
                if not _errs and set(_flux_periods) != set(_depth_periods):
                    _errs.append(
                        f"Return period mismatch between MomFlux and FlowDepth columns. "
                        f"MomFlux periods: {sorted(_flux_periods)}, FlowDepth periods: {sorted(_depth_periods)}"
                    )
            if _errs:
                logger.error("Input DataFrame validation failed:\n" + "\n".join(f"  - {e}" for e in _errs))
                raise ValueError(
                    "Input DataFrame validation failed:\n" +
                    "\n".join(f"  - {e}" for e in _errs)
                )
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

        with (
            resources.files("sphere.data")
            .joinpath("eqBuildingType.csv")
            .open("r", encoding="utf-8-sig") as bldg_type_file
        ):
            self._bldg_type_defaults = pd.read_csv(bldg_type_file)

        with (
            resources.files("sphere.data")
            .joinpath("eqBuildingArea.csv")
            .open("r", encoding="utf-8-sig") as bldg_area_file
        ):
            self._bldg_area_defaults = pd.read_csv(bldg_area_file)

        with (
            resources.files("sphere.data")
            .joinpath("hzOccupancyClass.csv")
            .open("r", encoding="utf-8-sig") as occ_class_file
        ):
            self._occupancy_defaults = pd.read_csv(occ_class_file)

        gdf = buildings.gdf

        # Check for building_height; fill missing/NaN values from eqBuildingType.csv (HeightDefault)
        bldg_height_col = buildings.fields.get_field_name('building_height')
        col_absent = bldg_height_col not in gdf.columns
        if not col_absent:
            gdf[bldg_height_col] = gdf[bldg_height_col].replace({'': np.nan, 0: np.nan})
            # treat numbers less than zero as NaN.
            gdf[bldg_height_col] = gdf[bldg_height_col].mask(
                pd.to_numeric(gdf[bldg_height_col], errors='coerce') < 0
            )
        n_null = 0 if col_absent else int(gdf[bldg_height_col].isna().sum())
        gdf['DefaultBldgHeight_Flag'] = False
        if col_absent or n_null > 0:
            eq_bldg_type_col = buildings.fields.get_field_name('eq_building_type')
            if eq_bldg_type_col and eq_bldg_type_col in gdf.columns:
                gdf[eq_bldg_type_col] = pd.to_numeric(gdf[eq_bldg_type_col].astype(str).str.strip(), errors='coerce')
                height_map = self._bldg_type_defaults.set_index('ID')['HeightDefault']
                ffh_field = buildings.fields.get_field_name('first_floor_height')
                if col_absent:
                    gdf['building_height'] = gdf[eq_bldg_type_col].map(height_map) + gdf[ffh_field]
                    buildings.fields.set_field_mapping('building_height', 'building_height')
                    bldg_height_col = 'building_height'
                    gdf['DefaultBldgHeight_Flag'] = True
                    logger.info(
                        "building_height not found in input data; using HeightDefault + first_floor_height from eqBuildingType.csv "
                        f"(joined on eq_building_type)."
                    )
                else:
                    null_mask = gdf[bldg_height_col].isna()
                    gdf[bldg_height_col] = gdf[bldg_height_col].fillna(
                        gdf[eq_bldg_type_col].map(height_map) + gdf[ffh_field]
                    )
                    gdf['DefaultBldgHeight_Flag'] = gdf['DefaultBldgHeight_Flag'] | null_mask
                    logger.info(
                        f"building_height column '{bldg_height_col}' had {n_null} NaN value(s); "
                        "filled from eqBuildingType.csv HeightDefault (joined on eq_building_type)."
                    )
                n_still_null = int(gdf[bldg_height_col].isna().sum())
                if n_still_null:
                    logger.warning(
                        f"{n_still_null} building(s) still have NaN building_height after applying defaults "
                        "(no matching BldgType in eqBuildingType.csv)."
                    )
            else:
                logger.warning(
                    "building_height not found/has NaN values and eq_building_type column is also absent; "
                    "cannot fill defaults from eqBuildingType.csv."
                )
        else:
            logger.info(f"building_height found in input data (column: '{bldg_height_col}'); using provided values.")

        # Check for lmh_rise; fill from eqBuildingType.csv (LMH_Rise) if absent/null
        lmh_rise_col = buildings.fields.get_field_name('lmh_rise')
        col_absent = lmh_rise_col not in gdf.columns
        if not col_absent:
            gdf[lmh_rise_col] = gdf[lmh_rise_col].replace({'': np.nan})
        n_null = 0 if col_absent else int(gdf[lmh_rise_col].isna().sum())
        if col_absent or n_null > 0:
            eq_bldg_type_col = buildings.fields.get_field_name('eq_building_type')
            if eq_bldg_type_col and eq_bldg_type_col in gdf.columns:
                gdf[eq_bldg_type_col] = pd.to_numeric(gdf[eq_bldg_type_col].astype(str).str.strip(), errors='coerce')
                rise_map = self._bldg_type_defaults.set_index('ID')['LMH_Rise']
                if col_absent:
                    gdf['lmh_rise'] = gdf[eq_bldg_type_col].map(rise_map)
                    buildings.fields.set_field_mapping('lmh_rise', 'lmh_rise')
                    lmh_rise_col = 'lmh_rise'
                    logger.info("lmh_rise not found in input data; using LMH_Rise from eqBuildingType.csv (joined on eq_building_type).")
                else:
                    null_mask = gdf[lmh_rise_col].isna()
                    gdf[lmh_rise_col] = gdf[lmh_rise_col].fillna(gdf[eq_bldg_type_col].map(rise_map))
                    logger.info(
                        f"lmh_rise column '{lmh_rise_col}' had {n_null} NaN value(s); "
                        "filled from eqBuildingType.csv LMH_Rise (joined on eq_building_type)."
                    )
                n_still_null = int(gdf[lmh_rise_col].isna().sum())
                if n_still_null:
                    logger.warning(
                        f"{n_still_null} building(s) still have NaN lmh_rise after applying defaults "
                        "(no matching ID in eqBuildingType.csv)."
                    )
            else:
                logger.warning(
                    "lmh_rise not found/has NaN values and eq_building_type column is also absent; "
                    "cannot fill defaults from eqBuildingType.csv."
                )
        else:
            logger.info(f"lmh_rise found in input data (column: '{lmh_rise_col}'); using provided values.")

        # Check for eq_building_type_class; populate from eqBuildingType.csv (BldgType) if absent/null
        eq_bldg_type_class_col = buildings.fields.get_field_name('eq_building_type_class')
        col_absent = eq_bldg_type_class_col not in gdf.columns
        if not col_absent:
            gdf[eq_bldg_type_class_col] = gdf[eq_bldg_type_class_col].replace({'': np.nan})
        n_null = 0 if col_absent else int(gdf[eq_bldg_type_class_col].isna().sum())
        if col_absent or n_null > 0:
            eq_bldg_type_col = buildings.fields.get_field_name('eq_building_type')
            if eq_bldg_type_col and eq_bldg_type_col in gdf.columns:
                gdf[eq_bldg_type_col] = pd.to_numeric(gdf[eq_bldg_type_col].astype(str).str.strip(), errors='coerce')
                class_map = self._bldg_type_defaults.set_index('ID')['BldgType']
                if col_absent:
                    gdf['eq_building_type_class'] = gdf[eq_bldg_type_col].map(class_map)
                    buildings.fields.set_field_mapping('eq_building_type_class', 'eq_building_type_class')
                    eq_bldg_type_class_col = 'eq_building_type_class'
                    logger.info("eq_building_type_class not found in input data; using BldgType from eqBuildingType.csv (joined on eq_building_type).")
                else:
                    null_mask = gdf[eq_bldg_type_class_col].isna()
                    gdf[eq_bldg_type_class_col] = gdf[eq_bldg_type_class_col].fillna(gdf[eq_bldg_type_col].map(class_map))
                    logger.info(
                        f"eq_building_type_class column '{eq_bldg_type_class_col}' had {n_null} NaN value(s); "
                        "filled from eqBuildingType.csv BldgType (joined on eq_building_type)."
                    )
                n_still_null = int(gdf[eq_bldg_type_class_col].isna().sum())
                if n_still_null:
                    logger.warning(
                        f"{n_still_null} building(s) still have NaN eq_building_type_class after applying defaults "
                        "(no matching ID in eqBuildingType.csv)."
                    )
            else:
                logger.warning(
                    "eq_building_type_class not found/has NaN values and eq_building_type column is also absent; "
                    "cannot fill defaults from eqBuildingType.csv."
                )
        else:
            logger.info(f"eq_building_type_class found in input data (column: '{eq_bldg_type_class_col}'); using provided values.")

        # Check for occupancy_type; derive from SOccupID (hzOccupancyClass.csv) if absent/null
        occ_col = buildings.fields.get_field_name('occupancy_type')
        col_absent = occ_col not in gdf.columns
        if not col_absent:
            gdf[occ_col] = gdf[occ_col].astype(str).str.strip().replace({'': np.nan, 'nan': np.nan})
        n_null = 0 if col_absent else int(gdf[occ_col].isna().sum())

        if not col_absent and n_null == 0:
            logger.info(f"Occupancy_Type found in input data (column: '{occ_col}'); using provided values.")
        else:
            soccup_col = buildings.fields.get_field_name('soccup_id')
            if not soccup_col or soccup_col not in gdf.columns:
                # Defensive: ttfBuildings already raises when both columns are absent.
                raise ValueError(
                    "Occupancy_Type not found and SOccupID column is also absent; cannot run analysis."
                )
            soccup_numeric = pd.to_numeric(gdf[soccup_col].astype(str).str.strip(), errors='coerce')
            occ_map = (
                self._occupancy_defaults
                .assign(Occupancy_Type=lambda d: d['Occupancy_Type'].astype(str).str.strip())
                .set_index('SOccupID')['Occupancy_Type']
            )
            derived = soccup_numeric.map(occ_map)
            if col_absent:
                gdf['occupancy_type'] = derived
                buildings.fields.set_field_mapping('occupancy_type', 'occupancy_type')
                occ_col = 'occupancy_type'
                logger.warning(
                    "Occupancy_Type not found in input data; deriving from SOccupID using "
                    "hzOccupancyClass.csv (joined on SOccupID)."
                )
            else:
                gdf[occ_col] = gdf[occ_col].fillna(derived)
                logger.warning(
                    f"Occupancy_Type column '{occ_col}' had {n_null} missing value(s); "
                    "derived from SOccupID using hzOccupancyClass.csv (joined on SOccupID)."
                )
            n_still_null = int(gdf[occ_col].isna().sum())
            if n_still_null:
                logger.warning(
                    f"{n_still_null} building(s) still have no Occupancy_Type after mapping "
                    "(no matching SOccupID in hzOccupancyClass.csv)."
                )

        # Flag Occupancy_Type values (provided or derived) that won't join to the economic
        # parameters (e.g. typos); these buildings get no economic losses from the left merge.
        valid_occ = set(self.econ_cap_params['Occupancy'].astype(str).str.strip())
        occ_vals = gdf[occ_col].astype(str).str.strip()
        unknown_mask = gdf[occ_col].notna() & ~occ_vals.isin(valid_occ)
        n_unknown = int(unknown_mask.sum())
        if n_unknown:
            bad_codes = sorted(occ_vals[unknown_mask].unique())
            logger.warning(
                f"{n_unknown} building(s) have Occupancy_Type value(s) not found in the economic "
                f"parameters (eqEconCapParams.csv); these buildings will receive no economic "
                f"losses. Unrecognized value(s): {bad_codes}."
            )

        # Check for area; fill missing/NaN values from eqBuildingArea.csv (SquareFootage)
        area_col = buildings.fields.get_field_name('area')
        col_absent = area_col not in gdf.columns
        if not col_absent:
            gdf[area_col] = gdf[area_col].replace({'': np.nan, 0: np.nan})
        n_null = 0 if col_absent else int(gdf[area_col].isna().sum())
        if col_absent or n_null > 0:
            occ_col = buildings.fields.get_field_name('occupancy_type')
            if occ_col and occ_col in gdf.columns:
                gdf[occ_col] = gdf[occ_col].astype(str).str.strip().replace('nan', np.nan)
                area_map = self._bldg_area_defaults.set_index('Occupancy')['SquareFootage']
                if col_absent:
                    gdf['area'] = gdf[occ_col].map(area_map)
                    buildings.fields.set_field_mapping('area', 'area')
                    area_col = 'area'
                    logger.info(
                        "area not found in input data; using SquareFootage from eqBuildingArea.csv "
                        "(joined on occupancy_type)."
                    )
                else:
                    null_mask = gdf[area_col].isna()
                    gdf[area_col] = gdf[area_col].fillna(gdf[occ_col].map(area_map))
                    logger.info(
                        f"area column '{area_col}' had {n_null} NaN value(s); "
                        "filled from eqBuildingArea.csv SquareFootage (joined on occupancy_type)."
                    )
                n_still_null = int(gdf[area_col].isna().sum())
                if n_still_null:
                    logger.warning(
                        f"{n_still_null} building(s) still have NaN area after applying defaults "
                        "(no matching Occupancy in eqBuildingArea.csv)."
                    )
            else:
                logger.warning(
                    "area not found/has NaN values and occupancy_type column is also absent; "
                    "cannot fill defaults from eqBuildingArea.csv."
                )
        else:
            logger.info(f"area found in input data (column: '{area_col}'); using provided values.")

        # Per-building caps / deductibles: read from input columns, fall back to the
        # scalar defaults (self.bldg_cap etc.) where blank/missing. 0 is a real value
        # for both caps and deductibles and is kept; only blank/missing gets the default.
        def _fill_scalar_default(prop_name, default_val, flag_col):
            col = buildings.fields.get_field_name(prop_name)
            col_absent = col not in gdf.columns
            if not col_absent:
                # to_numeric coerces '', whitespace-only, and non-numeric cells to NaN.
                gdf[col] = pd.to_numeric(gdf[col], errors='coerce')
                # treat numbers less than zero as NaN.
                gdf[col] = gdf[col].mask(gdf[col] < 0)
            n_null = 0 if col_absent else int(gdf[col].isna().sum())
            gdf[flag_col] = False
            if col_absent:
                gdf[prop_name] = float(default_val)
                buildings.fields.set_field_mapping(prop_name, prop_name)
                gdf[flag_col] = True
                logger.info(f"{prop_name} not found in input data; using default {default_val}.")
            elif n_null > 0:
                null_mask = gdf[col].isna()
                gdf[col] = gdf[col].fillna(float(default_val))
                gdf[flag_col] = null_mask
                logger.info(
                    f"{prop_name} column '{col}' had {n_null} blank/negative value(s); "
                    f"filled with default {default_val}."
                )
            else:
                logger.info(f"{prop_name} found in input data (column: '{col}'); using provided values.")
            # Guarantee no residual NaN before the column feeds adjust_loss_dedlim's sub/clip.
            final_col = buildings.fields.get_field_name(prop_name)
            n_still_null = int(gdf[final_col].isna().sum())
            if n_still_null:
                logger.warning(
                    f"{prop_name} column '{final_col}' still has {n_still_null} NaN value(s) after default fill."
                )

        _fill_scalar_default('bldg_cap',        self.bldg_cap,        'DefaultBldgCap_Flag')
        _fill_scalar_default('cont_cap',        self.cont_cap,        'DefaultContCap_Flag')
        _fill_scalar_default('bldg_deductible', self.bldg_deductible, 'DefaultBldgDeductible_Flag')
        _fill_scalar_default('cont_deductible', self.cont_deductible, 'DefaultContDeductible_Flag')


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
        logger.info(
            f"Starting TTF tsunami loss calculation for {len(gdf)} buildings "
            f"across {len(return_periods)} return period(s): {return_periods}"
        )

        # Compute depth in structure (flood_depth - first_floor_height) for NSD and content damage
        # Clamp to 0 minimum - negative values mean water doesn't reach structure (no damage)
        flood_depth_cols = self.buildings.fields.get_field_name('flood_depth')
        ffh_field = self.buildings.fields.get_field_name('first_floor_height')
        self.buildings.depth_in_structure = gdf[flood_depth_cols].sub(gdf[ffh_field], axis=0).clip(lower=0)

        # Check that all return-period column groups increase monotonically.
        # Group every GDF column that contains a return-period suffix (e.g. _100yr_)
        # by its prefix (MomFlux_, FlowDepth_, Speed_, …), then verify that values
        # are non-decreasing across sorted return periods for each group.
        _rp_groups: dict[str, list[tuple[int, str]]] = {}
        for _col in gdf.columns:
            _m = re.search(r'(\d+)yr', _col, re.IGNORECASE)
            if _m:
                _prefix = _col[:_m.start()]
                _rp_groups.setdefault(_prefix, []).append((int(_m.group(1)), _col))
        for _prefix, _rp_cols in _rp_groups.items():
            if len(_rp_cols) < 2:
                continue
            _sorted_cols = [c for _, c in sorted(_rp_cols)]
            _data = gdf[_sorted_cols].values
            _diffs = np.diff(_data, axis=1)
            _non_nan = _diffs[~np.isnan(_diffs)]
            if np.any(_non_nan < 0):
                _n = int(np.sum(np.any(_diffs < 0, axis=1)))
                logger.warning(
                    f"'{_prefix}*yr*' values do not monotonically increase across return periods "
                    f"for {_n} building(s)."
                )

        # Plausibility check — warn if all flux values are zero
        flux_vals = gdf[return_periods].values.ravel()
        if np.all(flux_vals[~np.isnan(flux_vals)] == 0):
            logger.warning("All momentum flux values are zero. Verify the correct input columns were provided.")

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

        # New flood-fill loss calculations (depth in structure / building height)
        bldg_height_field = self.buildings.fields.get_field_name('building_height')
        dis_cols = self.buildings.fields.get_field_name('depth_in_structure')
        fill_ratio = merged_df[dis_cols].div(
            merged_df[bldg_height_field].values, axis=0
        ).clip(0, 1)

        # Where structural damage > 70%, override fill_ratio to 1.0 (same mask applied to non-"new" losses above)
        dis_col_list = dis_cols if isinstance(dis_cols, list) else [dis_cols]
        for str_com_col, dis_col in zip(str_com_cols, dis_col_list):
            fill_ratio.loc[merged_df[str_com_col] > 0.7, dis_col] = 1.0

        cmp_nonstr_repair = merged_df['CmpNsaRepair'] + merged_df['CmpNsdRepair']

        # NewNonStructuralLoss = fill_ratio * ValStruct * (CmpNsaRepair + CmpNsdRepair) / 100
        merged_df[self.buildings.fields.get_field_name('new_nonstruct_loss')] = pd.DataFrame(
            fill_ratio.mul(cmp_nonstr_repair.values, axis=0).values / 100.0,
            dtype=float
        ).mul(merged_df[self.buildings.fields.get_field_name('building_cost')].values, axis=0)

        # NewContentLoss = fill_ratio * ValCont * CmpCntRepair / 100
        merged_df[self.buildings.fields.get_field_name('new_content_loss')] = pd.DataFrame(
            fill_ratio.mul(merged_df['CmpCntRepair'].values, axis=0).values / 100.0,
            dtype=float
        ).mul(merged_df[self.buildings.fields.get_field_name('content_cost')].values, axis=0)

        # NewInventoryLoss = fill_ratio * (Area * GrossSales * BusinessInv%) * (0.5) / 100
        new_inv_base = merged_df[self.buildings.fields.get_field_name('area')] * merged_df['GrossSales'].fillna(0) * merged_df['BusinessInv'].fillna(0)
        merged_df[self.buildings.fields.get_field_name('new_inventory_loss')] = pd.DataFrame(
            fill_ratio.mul(0.5, axis=0).values / 100.0,
            dtype=float
        ).mul(new_inv_base.values, axis=0)

        # NewTotalLoss = NewNonStructuralLoss + StructuralLoss (same as before since it's already accounting for depth) - this is essentially just a reweighting of the building loss based on depth in structure
        new_nonstruct_cols = self.buildings.fields.get_field_name('new_nonstruct_loss')
        merged_df[self.buildings.fields.get_field_name('new_total_loss')] = pd.DataFrame(
            merged_df[new_nonstruct_cols].values +
            merged_df[structloss_fields].values,
            dtype=float
        )

        # NewTotalEconomicLoss = New_building_loss + New_inventory_loss + relocation + income + rental + wage
        new_inventory_cols = self.buildings.fields.get_field_name('new_inventory_loss')
        new_content_cols = self.buildings.fields.get_field_name('new_content_loss')
        new_bldg_loss_cols = self.buildings.fields.get_field_name('new_total_loss')
        merged_df[self.buildings.fields.get_field_name('new_total_econ_loss')] = pd.DataFrame(
            merged_df[new_bldg_loss_cols].values +
            merged_df[new_inventory_cols].values +
            merged_df[new_content_cols].values +
            merged_df[self.buildings.fields.get_field_name('relocation_loss')].values +
            merged_df[self.buildings.fields.get_field_name('income_loss')].values +
            merged_df[self.buildings.fields.get_field_name('rental_loss')].values +
            merged_df[self.buildings.fields.get_field_name('wage_loss')].values,
            dtype=float
        )

        def calc_aal(losses_df):
            _df = losses_df.fillna(0.0)
            rp_cols = []
            for col in _df.columns.values:
                match = re.search(r"(\d+)(y)", col)
                if match:
                    rp_cols.append((int(match.group(1)), col))
            # ascending RP order required for correct trapezoidal integration
            rp_cols.sort()
            return_periods = [rp for rp, _ in rp_cols]
            losses_sorted = _df[[col for _, col in rp_cols]]

            sum_ann_loss = pd.DataFrame(0.0, index=_df.index, columns=return_periods, dtype=float)
            for i, p in enumerate(return_periods):
                if i == len(return_periods) - 1:
                    sum_ann_loss[p] = (1 / p) * losses_sorted.iloc[:, i]
                else:
                    next_p = return_periods[i + 1]
                    sum_ann_loss[p] = ((1 / p) - (1 / next_p)) * (losses_sorted.iloc[:, i] + losses_sorted.iloc[:, i + 1]) / 2
            # Debug: export annualized loss contribution per return period (summed across all buildings)
            # Useful for comparing trapezoidal integration against manual spreadsheet calculations.
            # Uncomment and set output_path to inspect.
            # output_path = r"outputs\debug_aal_by_rp.csv"
            # debug_df = pd.DataFrame({
            #     "return_period": return_periods,
            #     "annualized_probability": [1 / p for p in return_periods],
            #     "differential_probability": [
            #         (1 / p) if i == len(return_periods) - 1
            #         else (1 / p) - (1 / return_periods[i + 1])
            #         for i, p in enumerate(return_periods)
            #     ],
            #     "scenario_loss_total": [losses_sorted.iloc[:, i].sum() for i in range(len(return_periods))],
            #     "annualized_loss_total": [sum_ann_loss[p].sum() for p in return_periods],
            # })
            # debug_df["cumulative_aal"] = debug_df["annualized_loss_total"].cumsum()
            # debug_df.to_csv(output_path, index=False)
            return sum_ann_loss.sum(axis=1)
        
        def adjust_loss_dedlim(losses_df, ded=0, lim=1000000000):
            # ded / lim may be scalars or per-building Series aligned to losses_df.index.
            # axis=0 subtracts / clips row-wise across all return-period columns.
            llosses_df = losses_df.sub(ded, axis=0).clip(lower=0, upper=lim, axis=0)
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

        # Per-building deductible / cap columns (filled with user-provided scalar defaults
        # in __init__ where blank). These survive the how='left' merge into merged_df.
        bldg_cap_col = self.buildings.fields.get_field_name('bldg_cap')
        cont_cap_col = self.buildings.fields.get_field_name('cont_cap')
        bldg_ded_col = self.buildings.fields.get_field_name('bldg_deductible')
        cont_ded_col = self.buildings.fields.get_field_name('cont_deductible')

        # Compute Gross Building Losses
        merged_df[self.buildings.fields.get_field_name('gross_building_loss')] = adjust_loss_dedlim(
            merged_df[self.buildings.fields.get_field_name('building_loss')],
            merged_df[bldg_ded_col],
            merged_df[bldg_cap_col],
        )

        # Compute Gross Content Losses
        merged_df[self.buildings.fields.get_field_name('gross_content_loss')] = adjust_loss_dedlim(
            merged_df[self.buildings.fields.get_field_name('content_loss')],
            merged_df[cont_ded_col],
            merged_df[cont_cap_col],
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

        # Compute Gross New Total Loss (deductible/cap applied to combined new total)
        merged_df[self.buildings.fields.get_field_name('gross_new_total_loss')] = adjust_loss_dedlim(
            merged_df[self.buildings.fields.get_field_name('new_total_loss')],
            merged_df[bldg_ded_col],
            merged_df[bldg_cap_col],
        )

        # Compute Gross New Content Loss (deductible/cap applied to new content loss)
        merged_df[self.buildings.fields.get_field_name('gross_New_content_loss')] = adjust_loss_dedlim(
            merged_df[self.buildings.fields.get_field_name('new_content_loss')],
            merged_df[cont_ded_col],
            merged_df[cont_cap_col],
        )

        # Compute New Loss AALs
        merged_df[self.buildings.fields.get_field_name('new_nonstruct_loss_aal')] = calc_aal(
            merged_df[self.buildings.fields.get_field_name('new_nonstruct_loss')]
        )
        merged_df[self.buildings.fields.get_field_name('new_content_loss_aal')] = calc_aal(
            merged_df[self.buildings.fields.get_field_name('new_content_loss')]
        )
        merged_df[self.buildings.fields.get_field_name('new_inventory_loss_aal')] = calc_aal(
            merged_df[self.buildings.fields.get_field_name('new_inventory_loss')]
        )
        merged_df[self.buildings.fields.get_field_name('new_total_loss_aal')] = calc_aal(
            merged_df[self.buildings.fields.get_field_name('new_total_loss')]
        )
        merged_df[self.buildings.fields.get_field_name('gross_new_total_loss_aal')] = calc_aal(
            merged_df[self.buildings.fields.get_field_name('gross_new_total_loss')]
        )
        merged_df[self.buildings.fields.get_field_name('gross_New_content_loss_aal')] = calc_aal(
            merged_df[self.buildings.fields.get_field_name('gross_New_content_loss')]
        )
        merged_df[self.buildings.fields.get_field_name('NewBldgAAL_lossratio_USDperM')] = (
            merged_df[self.buildings.fields.get_field_name('new_total_loss_aal')] /
            (merged_df[self.buildings.fields.get_field_name('building_cost')] / 1_000_000)
        )
        merged_df[self.buildings.fields.get_field_name('GrossNewBldgAAL_LossRatio_USDperM')] = (
            merged_df[self.buildings.fields.get_field_name('gross_new_total_loss_aal')] /
            (merged_df[self.buildings.fields.get_field_name('building_cost')] / 1_000_000)
        )
        merged_df[self.buildings.fields.get_field_name('NewCapitalLoss_AAL')] = (
            merged_df[self.buildings.fields.get_field_name('new_total_loss_aal')]
                .add(merged_df[self.buildings.fields.get_field_name('new_content_loss_aal')].values)
                .add(merged_df[self.buildings.fields.get_field_name('new_inventory_loss_aal')].values)
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

        merged_df[self.buildings.fields.get_field_name('NewTotalEconomicLoss_AAL')] = (
            merged_df[self.buildings.fields.get_field_name('NewCapitalLoss_AAL')]
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