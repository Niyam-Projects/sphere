import logging
import re
import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
from unittest.mock import patch

from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.buildings import ttfBuildings
from sphere.tsunami.analysis.hazus_tsunami import HazusTsunamiAnalysis
from sphere.tsunami.analysis.ttf_aal_analysis import ttfAALAnalysis
from sphere.tsunami.default_vulnerability import DefaultTsunamiVulnerability
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader


class MockRasterReader(AbstractRasterReader):
    """Mock raster reader that returns the values from the CSV."""
    
    def __init__(self, values: pd.DataFrame):
        """Initialize with a pandas Series of values."""
        self.values = values
    
    def get_value(self, lon: float, lat: float) -> float:
        return self.values[0]  # Not used in this test

    def get_value_vectorized(self, geometries):
        """Return the stored values in the same order."""
        return self.values.to_frame()

class MockRasterReaderTTF(AbstractRasterReader):
    """Mock raster reader that returns the values from the CSV."""
    
    def __init__(self, values: pd.DataFrame):
        """Initialize with a pandas DataFrame of values."""
        self.values = values
    
    def get_value(self, lon: float, lat: float) -> float:
        return self.values.iloc[0, 0]  # Not used in this test

    def get_value_vectorized(self, geometries):
        """Return the stored values in the same order."""
        return self.values

@pytest.fixture
def nsi_buildings_data():
    """Load NSI results CSV and prepare building data."""
    csv_path = Path(__file__).parent / "data" / "nsi_results.csv"
    df = pd.read_csv(csv_path)
    
    # Create geometry from X, Y coordinates
    geometry = [Point(xy) for xy in zip(df['X'], df['Y'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    
    # Store expected loss values before creating Buildings object
    expected_losses = {
        'BldgLossUSD': df['BldgLossUSD'].values,
        'ContentLossUSD': df['ContentLossUSD'].values,
        'RelocationLossUSD': df['RelocationLossUSD'].values,
        'IncomeLossUSD': df['IncomeLossUSD'].values,
        'RentalLossUSD': df['RentalLossUSD'].values,
        'WageLossUSD': df['WageLossUSD'].values,
    }
    
    # Map NSI fields to Buildings schema using dictionary
    field_mapping = {
        'occupancy_type': 'Occupancy',
        'num_stories': 'NUM_STORY',
        'first_floor_height': 'FOUND_HT',
        'foundation_type': 'FNDTYPE',
        'area': 'SQFT',
        'building_cost': 'Hazus_Building_Values',
        'content_cost': 'Hazus_Content_Values',
        'flood_depth': 'flood_depth',
        'flux': 'flux',
        'eq_building_type': 'EqBldgTypeId_SI',
    }
    
    # Remove loss columns from the dataframe
    loss_columns = ['BldgLossUSD', 'ContentLossUSD', 'RelocationLossUSD', 
                    'IncomeLossUSD', 'RentalLossUSD', 'WageLossUSD',
                    'StructLoss', 'NonStrLoss']
    gdf = gdf.drop(columns=[col for col in loss_columns if col in gdf.columns])
    
    # Create Buildings object with field mapping
    buildings = Buildings(gdf=gdf) #, overrides=field_mapping)
    
    # Store the original depth and flux values for the mock rasters
    depth_values = df['flood_depth']
    flux_values = df['flux']
    
    return buildings, expected_losses, depth_values, flux_values

@pytest.fixture
def ttf_buildings_data():
    """Load NSI results CSV and prepare building data."""
    # csv_path = Path(__file__).parent / "data" / "new"/ "Oahu_Output_TTF_Hazus_wArea_HAZUS_Extended.csv"
    # csv_path = Path(__file__).parent / "data" / "new" / "Output_NSI_WA_pilot_wArea_HAZUS_Extended_wOccType.csv"
    csv_path = Path(__file__).parent / "data" / "new" / "Output_NSI_OR_pilot_wArea_HAZUS_Extended_wOccType.csv"
    df = pd.read_csv(csv_path)
    
    # Create geometry from X, Y coordinates
    geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    
    # Map NSI fields to Buildings schema using dictionary
    field_mapping = {
        'occupancy_type': 'SOccupID',
        # 'num_stories': 'NUM_STORY',
        'first_floor_height': 'FirstFloor',
        # 'foundation_type': 'FNDTYPE',
        # 'area': 'SQFT',
        'building_cost': 'ValStruct',
        'content_cost': 'ValCont',
        'eq_building_type': 'EqBldgType',
    }
    
    # Grab all fields from gdf columns that start with "MomFlux" or "FlowDepth"
    import re
    flux_return_list = []
    flood_return_list = []
    for col in gdf.columns:
        if col.lower().startswith("momflux"):
            # Use regex to create an alias where the key value is "momflux" + the return period (e.g., "momflux100")
            match = re.match(r"(momflux_)(\d+yr)", col.lower())
            if match:
                alias_key = f"{match.group(1)}{match.group(2)}"
                field_mapping[alias_key] = [col]
            flux_return_list.append(col)
        elif col.lower().startswith("flowdepth"):
            # Use regex to create an alias where the key value is "flowdepth" + the return period (e.g., "flowdepth100")
            match = re.match(r"(flowdepth_)(\d+yr)", col.lower())
            if match:
                alias_key = f"{match.group(1)}{match.group(2)}"
                field_mapping[alias_key] = [col]
            flood_return_list.append(col)
    
    # Create Buildings object with field mapping
    buildings = ttfBuildings(gdf=gdf) #, overrides=field_mapping)
    
    # Store the original depth and flux values for the mock rasters
    depth_values = df[flood_return_list]
    flux_values = df[flux_return_list]
    
    return buildings, depth_values, flux_values

@pytest.fixture
def mock_rasters_ttf(ttf_buildings_data):
    """Create mock raster readers using the CSV data."""
    buildings, depth_values, flux_values = ttf_buildings_data
    
    # depth_raster = MockRasterReader(depth_values)
    # flux_raster = MockRasterReader(flux_values)
    
    # Actually we need to reverse the raster calculations that will happen later on for this test
    depth_raster = MockRasterReaderTTF((depth_values + buildings.first_floor_height.to_frame().values) / (2.0 / 3.0 * 1250.0 / 381.0))
    flux_raster = MockRasterReaderTTF(flux_values / (2.0 / 3.0 * (1250.0 ** 3 / 381.0 ** 3)))
    
    return depth_raster, flux_raster

@pytest.fixture
def mock_rasters(nsi_buildings_data):
    """Create mock raster readers using the CSV data."""
    buildings, _, depth_values, flux_values = nsi_buildings_data
    
    # depth_raster = MockRasterReader(depth_values)
    # flux_raster = MockRasterReader(flux_values)
    
    # Actually we need to reverse the raster calculations that will happen later on for this test
    depth_raster = MockRasterReader((depth_values + buildings.first_floor_height) / (2.0 / 3.0 * 1250.0 / 381.0))
    flux_raster = MockRasterReader(flux_values / (2.0 / 3.0 * (1250.0 ** 3 / 381.0 ** 3)))
    
    return depth_raster, flux_raster


def test_tsunami_analysis_with_nsi_data(nsi_buildings_data, mock_rasters):
    """Test tsunami analysis with NSI results data."""
    buildings, expected_losses, _, _ = nsi_buildings_data
    depth_raster, flux_raster = mock_rasters
    
    # Create vulnerability function
    vulnerability_func = DefaultTsunamiVulnerability()
    
    # Create analysis object
    analysis = HazusTsunamiAnalysis(
        buildings=buildings,
        vulnerability_func=vulnerability_func,
        depth_grid=depth_raster,
        momentum_flux=flux_raster
    )
    
    # Calculate losses
    result_df = analysis.calculate_losses()
    
    # Verify the analysis ran successfully
    assert result_df is not None
    assert len(result_df) == len(expected_losses['BldgLossUSD'])
    
    # Compare computed losses with expected values
    # Use relative tolerance for floating point comparison
    rtol = 0.05  # 5% relative tolerance
    computed_building_loss = result_df[buildings.fields.get_field_name('building_loss')].values
    # pd.DataFrame(computed_building_loss).to_csv("computed_building_loss.csv")
    # pd.DataFrame(expected_losses['BldgLossUSD']).to_csv("expected_building_loss.csv")
    # pd.DataFrame(result_df['p_nsd_comp'].values).to_csv("computed_p_nsd_comp.csv")
    np.testing.assert_allclose(
        computed_building_loss,
        expected_losses['BldgLossUSD'],
        rtol=rtol,
        err_msg="Building loss values don't match expected"
    )
    
    computed_content_loss = result_df[buildings.fields.get_field_name('content_loss')].values
    np.testing.assert_allclose(
        computed_content_loss,
        expected_losses['ContentLossUSD'],
        rtol=rtol,
        err_msg="Content loss values don't match expected"
    )
    
    computed_relocation_loss = result_df[buildings.fields.get_field_name('relocation_loss')].values
    np.testing.assert_allclose(
        computed_relocation_loss,
        expected_losses['RelocationLossUSD'],
        rtol=rtol,
        err_msg="Relocation loss values don't match expected"
    )
    
    computed_income_loss = result_df[buildings.fields.get_field_name('income_loss')].values
    np.testing.assert_allclose(
        computed_income_loss,
        expected_losses['IncomeLossUSD'],
        rtol=rtol,
        err_msg="Income loss values don't match expected"
    )
    
    computed_rental_loss = result_df[buildings.fields.get_field_name('rental_loss')].values
    np.testing.assert_allclose(
        computed_rental_loss,
        expected_losses['RentalLossUSD'],
        rtol=rtol,
        err_msg="Rental loss values don't match expected"
    )
    
    computed_wage_loss = result_df[buildings.fields.get_field_name('wage_loss')].values
    np.testing.assert_allclose(
        computed_wage_loss,
        expected_losses['WageLossUSD'],
        rtol=rtol,
        err_msg="Wage loss values don't match expected"
    )


def test_tsunami_analysis_basic_run(nsi_buildings_data, mock_rasters):
    """Basic test to ensure the analysis completes without errors."""
    buildings, _, _, _ = nsi_buildings_data
    depth_raster, flux_raster = mock_rasters
    
    vulnerability_func = DefaultTsunamiVulnerability()
    
    analysis = HazusTsunamiAnalysis(
        buildings=buildings,
        vulnerability_func=vulnerability_func,
        depth_grid=depth_raster,
        momentum_flux=flux_raster
    )
    
    result_df = analysis.calculate_losses()
    
    # Basic assertions
    assert result_df is not None
    assert len(result_df) > 0
    assert buildings.fields.get_field_name('building_loss') in result_df.columns
    assert buildings.fields.get_field_name('content_loss') in result_df.columns
    assert buildings.fields.get_field_name('relocation_loss') in result_df.columns

def test_ttf_tsunami_analysis(ttf_buildings_data, mock_rasters_ttf):
    """Test tsunami analysis with NSI results data."""
    buildings, _, _ = ttf_buildings_data
    depth_raster, flux_raster = mock_rasters_ttf
    
    # Create vulnerability function
    vulnerability_func = DefaultTsunamiVulnerability()
    
    # Create analysis object
    analysis = HazusTsunamiAnalysis(
        buildings=buildings,
        vulnerability_func=vulnerability_func,
        depth_grid=depth_raster,
        momentum_flux=flux_raster
    )
    
    # Calculate losses
    print("Calculating losses for TTF data...")
    result_df = analysis.calculate_losses()
    # result_df.to_csv("ttf_result_losses.csv") # This file is quite large!
    
    # # Verify the analysis ran successfully
    assert result_df is not None
    # assert len(result_df) == len(expected_losses['BldgLossUSD'])
    
    # # Compare computed losses with expected values
    # # Use relative tolerance for floating point comparison
    # rtol = 0.05  # 5% relative tolerance
    # computed_building_loss = result_df[buildings.fields.get_field_name('building_loss')].values
    # pd.DataFrame(computed_building_loss).to_csv("computed_building_loss.csv")
    # pd.DataFrame(expected_losses['BldgLossUSD']).to_csv("expected_building_loss.csv")
    # pd.DataFrame(result_df['p_nsd_comp'].values).to_csv("computed_p_nsd_comp.csv")
    # np.testing.assert_allclose(
    #     computed_building_loss,
    #     expected_losses['BldgLossUSD'],
    #     rtol=rtol,
    #     err_msg="Building loss values don't match expected"
    # )
    
    # computed_content_loss = result_df[buildings.fields.get_field_name('content_loss')].values
    # np.testing.assert_allclose(
    #     computed_content_loss,
    #     expected_losses['ContentLossUSD'],
    #     rtol=rtol,
    #     err_msg="Content loss values don't match expected"
    # )
    
    # computed_relocation_loss = result_df[buildings.fields.get_field_name('relocation_loss')].values
    # np.testing.assert_allclose(
    #     computed_relocation_loss,
    #     expected_losses['RelocationLossUSD'],
    #     rtol=rtol,
    #     err_msg="Relocation loss values don't match expected"
    # )
    
    # computed_income_loss = result_df[buildings.fields.get_field_name('income_loss')].values
    # np.testing.assert_allclose(
    #     computed_income_loss,
    #     expected_losses['IncomeLossUSD'],
    #     rtol=rtol,
    #     err_msg="Income loss values don't match expected"
    # )
    
    # computed_rental_loss = result_df[buildings.fields.get_field_name('rental_loss')].values
    # np.testing.assert_allclose(
    #     computed_rental_loss,
    #     expected_losses['RentalLossUSD'],
    #     rtol=rtol,
    #     err_msg="Rental loss values don't match expected"
    # )
    
    # computed_wage_loss = result_df[buildings.fields.get_field_name('wage_loss')].values
    # np.testing.assert_allclose(
    #     computed_wage_loss,
    #     expected_losses['WageLossUSD'],
    #     rtol=rtol,
    #     err_msg="Wage loss values don't match expected"
    # )


def test_ttf_aal_warns_non_monotonic_flux_values(caplog):
    """ttfAALAnalysis logs a warning when flux data values decrease across return period columns."""
    n = 3
    # MomFlux_100yr values are HIGHER than MomFlux_250yr — non-monotonic data
    gdf = gpd.GeoDataFrame(
        {
            'Occupancy_Type': ['RES1'] * n,
            'AreaSqft': [1500.0] * n,
            'ValStruct': [200_000.0] * n,
            'ValCont': [50_000.0] * n,
            'FirstFloor': [1.0] * n,
            'EqBldgType': ['W1'] * n,
            'MomFlux_100yr_Median': [10.0, 8.0, 6.0],
            'MomFlux_250yr_Median': [5.0, 4.0, 3.0],   # lower than 100yr → violation
            'FlowDepth_100yr_Median': [5.0, 4.0, 3.0],
            'FlowDepth_250yr_Median': [8.0, 7.0, 6.0],
        },
        geometry=gpd.points_from_xy([-122.0] * n, [47.0] * n),
        crs="EPSG:4326",
    )

    buildings = ttfBuildings(gdf=gdf)
    vulnerability_func = DefaultTsunamiVulnerability()
    analysis = ttfAALAnalysis(buildings=buildings, vulnerability_func=vulnerability_func)

    with caplog.at_level(logging.WARNING):
        with patch.object(vulnerability_func, 'compute_damage_states'):
            try:
                analysis.calculate_losses()
            except Exception:
                # The warning fires before compute_damage_states; ignore downstream
                # errors caused by missing probability columns from the patched no-op.
                pass

    assert any(
        "do not monotonically increase" in record.message
        for record in caplog.records
        if record.levelno == logging.WARNING
    ), "Expected a warning about non-monotonic flux values, but none was logged."


def test_ttf_aal_no_warning_monotonic_flux_values(caplog):
    """ttfAALAnalysis does NOT warn when flux data values increase monotonically across columns."""
    n = 3
    # MomFlux_250yr > MomFlux_100yr — correct monotonic order
    gdf = gpd.GeoDataFrame(
        {
            'Occupancy_Type': ['RES1'] * n,
            'AreaSqft': [1500.0] * n,
            'ValStruct': [200_000.0] * n,
            'ValCont': [50_000.0] * n,
            'FirstFloor': [1.0] * n,
            'EqBldgType': ['W1'] * n,
            'MomFlux_100yr_Median': [3.0, 4.0, 5.0],
            'MomFlux_250yr_Median': [6.0, 7.0, 8.0],   # higher than 100yr → OK
            'FlowDepth_100yr_Median': [3.0, 4.0, 5.0],
            'FlowDepth_250yr_Median': [6.0, 7.0, 8.0],
        },
        geometry=gpd.points_from_xy([-122.0] * n, [47.0] * n),
        crs="EPSG:4326",
    )

    buildings = ttfBuildings(gdf=gdf)
    vulnerability_func = DefaultTsunamiVulnerability()
    analysis = ttfAALAnalysis(buildings=buildings, vulnerability_func=vulnerability_func)

    with caplog.at_level(logging.WARNING):
        with patch.object(vulnerability_func, 'compute_damage_states'):
            try:
                analysis.calculate_losses()
            except Exception:
                pass

    assert not any(
        "do not monotonically increase" in record.message
        for record in caplog.records
        if record.levelno == logging.WARNING
    ), "Unexpected warning about non-monotonic flux values for valid monotonic data."


# ---------------------------------------------------------------------------
# calc_aal: all return-period detection tests
# ---------------------------------------------------------------------------

def _make_aal_buildings():
    """ttfBuildings with 3 return periods (100yr, 250yr, 500yr) for AAL tests."""
    gdf = gpd.GeoDataFrame(
        {
            # one residential, one commercial so all loss categories are non-zero
            'Occupancy_Type':        ['RES1', 'COM4'],
            'AreaSqft':              [1500.0, 2000.0],
            'ValStruct':             [200_000.0, 500_000.0],
            'ValCont':               [50_000.0, 125_000.0],
            'FirstFloor':            [1.0, 2.0],
            'EqBldgType':            [1, 1],
            'building_height':       [12.0, 14.0],
            'MomFlux_100yr_Median':  [5.0,  8.0],
            'MomFlux_250yr_Median':  [10.0, 15.0],
            'MomFlux_500yr_Median':  [15.0, 22.0],
            'FlowDepth_100yr_Median':[2.0,  3.0],
            'FlowDepth_250yr_Median':[4.0,  6.0],
            'FlowDepth_500yr_Median':[6.0,  9.0],
            # Inject inventory params so they survive both economic CSV merges.
            # Suffix rules ('', '_econCap'/'_econInc') mean the GDF column wins as the
            # un-suffixed name; the joined CSV value lands in the suffixed column and is
            # never referenced by the loss calc.  In production a user GDF with matching
            # column names would silently override CSV values the same way — a footgun to
            # document, but intentional here.
            'GrossSales':            [0.0, 200.0],   # $/sqft/yr; 0 for residential
            'BusinessInv':           [0.0,  15.0],   # % of gross sales held as inventory
            'ModInvDmg':             [0.0,   2.0],   # % inventory damaged at moderate DS
            'ExtInvDmg':             [0.0,  10.0],   # % at extensive DS
            'CmpInvDmg':             [0.0,  50.0],   # % at complete DS
        },
        geometry=gpd.points_from_xy([-122.0, -122.1], [47.0, 47.1]),
        crs='EPSG:4326',
    )
    return ttfBuildings(gdf=gdf)


def _inject_damage_probs(buildings_obj):
    """
    Drop-in replacement for compute_damage_states.
    Injects deterministic probabilities (all str_complete < 0.7) directly into
    buildings_obj.gdf so calculate_losses can proceed without fragility curves.
    Values increase with return period so per-RP losses differ (non-vacuous test).
    """
    # (str_comp, str_ext, str_mod, str_none,
    #  nsd_comp, nsd_ext, nsd_mod, nsd_none,
    #  cont_comp, cont_ext, cont_mod, cont_none)
    by_rp = {
        '100y': (0.10, 0.20, 0.30, 0.40,  0.10, 0.20, 0.30, 0.40,  0.10, 0.20, 0.30, 0.40),
        '250y': (0.20, 0.25, 0.30, 0.25,  0.20, 0.25, 0.30, 0.25,  0.20, 0.25, 0.30, 0.25),
        '500y': (0.40, 0.25, 0.20, 0.15,  0.40, 0.25, 0.20, 0.15,  0.40, 0.25, 0.20, 0.15),
    }
    for rp, vals in by_rp.items():
        sc, se, sm, sn, nc, ne, nm, nn, cc, ce, cm, cn = vals
        buildings_obj.gdf[f'p_str_comp_{rp}']  = sc
        buildings_obj.gdf[f'p_str_ext_{rp}']   = se
        buildings_obj.gdf[f'p_str_mod_{rp}']   = sm
        buildings_obj.gdf[f'p_str_none_{rp}']  = sn
        buildings_obj.gdf[f'p_nsd_comp_{rp}']  = nc
        buildings_obj.gdf[f'p_nsd_ext_{rp}']   = ne
        buildings_obj.gdf[f'p_nsd_mod_{rp}']   = nm
        buildings_obj.gdf[f'p_nsd_none_{rp}']  = nn
        buildings_obj.gdf[f'p_cont_comp_{rp}'] = cc
        buildings_obj.gdf[f'p_cont_ext_{rp}']  = ce
        buildings_obj.gdf[f'p_cont_mod_{rp}']  = cm
        buildings_obj.gdf[f'p_cont_none_{rp}'] = cn


def _expected_aal(result_df, loss_cols):
    """
    Reference trapezoidal AAL matching calc_aal's formula exactly.
    Sorts columns by ascending return period before integrating.
    """
    pairs = sorted(
        [
            (int(re.search(r'(\d+)y', c).group(1)), result_df[c].to_numpy(dtype=float))
            for c in loss_cols
            if re.search(r'(\d+)y', c)
        ],
        key=lambda x: x[0],
    )
    aal = np.zeros(len(pairs[0][1]))
    for i, (p, L) in enumerate(pairs):
        if i == len(pairs) - 1:
            aal += L / p
        else:
            next_p = pairs[i + 1][0]
            aal += ((1 / p) - (1 / next_p)) * (L + pairs[i + 1][1]) / 2
    return aal


@pytest.fixture(scope='module')
def aal_test_result():
    """Run calculate_losses once with mocked damage states; cache for all AAL tests."""
    buildings = _make_aal_buildings()
    vf = DefaultTsunamiVulnerability()
    analysis = ttfAALAnalysis(buildings=buildings, vulnerability_func=vf)
    with patch.object(vf, 'compute_damage_states', side_effect=_inject_damage_probs):
        result = analysis.calculate_losses()
    return result, buildings


@pytest.mark.parametrize("loss_field,aal_field", [
    ("building_loss",      "building_loss_aal"),
    ("content_loss",       "content_loss_aal"),
    ("relocation_loss",    "relocation_loss_aal"),
    ("income_loss",        "income_loss_aal"),
    ("rental_loss",        "rental_loss_aal"),
    ("wage_loss",          "wage_loss_aal"),
    ("inventory_loss",     "inventory_loss_aal"),
    ("new_nonstruct_loss", "new_nonstruct_loss_aal"),
    ("new_content_loss",   "new_content_loss_aal"),
    ("new_inventory_loss", "new_inventory_loss_aal"),
    ("new_total_loss",     "new_total_loss_aal"),
])
def test_calc_aal_all_return_periods_detected(loss_field, aal_field, aal_test_result):
    """
    calc_aal must detect and integrate all 3 return periods for every loss category.
    Expected AAL is the hand-rolled trapezoidal sum over the per-RP loss columns.
    A mismatch (or all-zero losses) means a return period was silently dropped.
    """
    result, buildings = aal_test_result
    loss_cols = buildings.fields.get_field_name(loss_field)
    aal_col   = buildings.fields.get_field_name(aal_field)

    assert isinstance(loss_cols, list) and len(loss_cols) == 3, (
        f"{loss_field}: expected 3 RP columns, got {loss_cols}"
    )

    expected = _expected_aal(result, loss_cols)
    computed = result[aal_col].to_numpy(dtype=float)

    # Vacuous-test guard: at least one building must have a non-zero loss
    assert np.any(np.isfinite(expected) & (expected != 0)), (
        f"{loss_field} is zero for all buildings — mock probabilities or occupancy "
        "type produced no losses; the test would pass trivially."
    )

    np.testing.assert_allclose(
        computed, expected, rtol=1e-9,
        err_msg=(
            f"{aal_field}: computed AAL differs from 3-period trapezoidal expected. "
            "Likely a return period was dropped or ordering was wrong in calc_aal."
        ),
    )


def _minimal_ttf_gdf(with_occ=False, with_soccup=True, with_eq_bldg_type=True, eq_bldg_type_class=None):
    """Minimal gdf accepted by ttfBuildings / ttfAALAnalysis.__init__.

    EqBldgType=1 -> BldgType 'W1' (HeightDefault 14, LMH_Rise 'L')
    EqBldgType=2 -> BldgType 'W2' (HeightDefault 24, LMH_Rise 'L')
    per eqBuildingType.csv.
    """
    data = {
        'NsiID': [1, 2],
        'ValStruct': [100000.0, 200000.0],
        'ValCont': [50000.0, 100000.0],
        'FirstFloor': [1.0, 1.0],
        'MomFlux_100yr_Median_ft3_per_sec2': [10.0, 20.0],
        'FlowDepth_100yr_Median_ft': [3.0, 4.0],
        'Longitude': [-122.0, -122.1],
        'Latitude': [45.0, 45.1],
    }
    if with_eq_bldg_type:
        data['EqBldgType'] = [1, 2]
    if eq_bldg_type_class is not None:
        data['EqBldgTypeClass'] = eq_bldg_type_class
    if with_soccup:
        data['SOccupID'] = [1, 3]      # -> RES1, RES3A in hzOccupancyClass.csv
    if with_occ:
        data['Occupancy_Type'] = ['RES1', 'RES3A']
    df = pd.DataFrame(data)
    geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
    return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


def test_occupancy_type_derived_from_soccupid(caplog):
    """Occupancy_Type absent but SOccupID present -> derived via hzOccupancyClass.csv, warned."""
    gdf = _minimal_ttf_gdf(with_occ=False, with_soccup=True)
    buildings = ttfBuildings(gdf=gdf)
    with caplog.at_level(logging.WARNING):
        ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    occ_col = buildings.fields.get_field_name('occupancy_type')
    assert buildings.gdf[occ_col].tolist() == ['RES1', 'RES3A']
    assert any('deriving from SOccupID' in r.message.lower() or
               'derived from soccupid' in r.message.lower() or
               'SOccupID' in r.message for r in caplog.records)


def test_occupancy_type_partial_fill_from_soccupid():
    """Occupancy_Type present with a blank row -> that row backfilled from SOccupID."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=True)
    gdf.loc[1, 'Occupancy_Type'] = ''   # blank second row
    buildings = ttfBuildings(gdf=gdf)
    ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    occ_col = buildings.fields.get_field_name('occupancy_type')
    assert buildings.gdf[occ_col].tolist() == ['RES1', 'RES3A']


def test_missing_occupancy_and_soccupid_raises():
    """Neither Occupancy_Type nor SOccupID -> cannot run analysis."""
    gdf = _minimal_ttf_gdf(with_occ=False, with_soccup=False)
    with pytest.raises(ValueError):
        ttfBuildings(gdf=gdf)


def test_unrecognized_occupancy_type_warns(caplog):
    """A typo'd Occupancy_Type that won't join the economic params is warned about."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False)
    gdf.loc[1, 'Occupancy_Type'] = 'RES1X'   # typo -> not in eqEconCapParams.csv
    buildings = ttfBuildings(gdf=gdf)
    with caplog.at_level(logging.WARNING):
        ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    assert any('RES1X' in r.message and 'not found in the economic parameters' in r.message
               for r in caplog.records)


# ---------------------------------------------------------------------------
# eq_building_type / eq_building_type_class / building_height / lmh_rise / area
# default-fill (backfill-from-lookup) tests. These pin current behavior before
# the fill blocks get generalized into a shared helper.
# ---------------------------------------------------------------------------

def test_eq_building_type_derived_from_class(caplog):
    """EqBldgType absent but EqBldgTypeClass present -> ID derived via eqBuildingType.csv (BldgType->ID)."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False, with_eq_bldg_type=False,
                            eq_bldg_type_class=['W1', 'W2'])
    buildings = ttfBuildings(gdf=gdf)
    with caplog.at_level(logging.INFO):
        ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    id_col = buildings.fields.get_field_name('eq_building_type')
    assert buildings.gdf[id_col].tolist() == [1, 2]
    assert any('using id from eqbuildingtype.csv' in r.message.lower() for r in caplog.records)


def test_eq_building_type_partial_fill_from_class():
    """EqBldgType present with a blank row -> that row backfilled from EqBldgTypeClass."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False, eq_bldg_type_class=['W1', 'W2'])
    gdf.loc[1, 'EqBldgType'] = np.nan
    buildings = ttfBuildings(gdf=gdf)
    ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    id_col = buildings.fields.get_field_name('eq_building_type')
    assert buildings.gdf[id_col].tolist() == [1.0, 2.0]


def test_missing_eq_building_type_and_class_warns(caplog):
    """Neither EqBldgType nor EqBldgTypeClass present -> warned, not raised."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False, with_eq_bldg_type=False)
    buildings = ttfBuildings(gdf=gdf)
    with caplog.at_level(logging.WARNING):
        ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    assert any('eq_building_type_class column is also' in r.message for r in caplog.records)


def test_eq_building_type_class_derived_from_id():
    """EqBldgTypeClass absent but EqBldgType present -> Class derived via eqBuildingType.csv (ID->BldgType)."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False)   # EqBldgType = [1, 2]
    buildings = ttfBuildings(gdf=gdf)
    ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    class_col = buildings.fields.get_field_name('eq_building_type_class')
    assert buildings.gdf[class_col].tolist() == ['W1', 'W2']


def test_building_height_and_lmh_rise_default_from_id():
    """building_height/lmh_rise absent -> filled via eqBuildingType.csv keyed on EqBldgType ID."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False)   # EqBldgType = [1, 2], FirstFloor = [1.0, 1.0]
    buildings = ttfBuildings(gdf=gdf)
    ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    height_col = buildings.fields.get_field_name('building_height')
    lmh_col = buildings.fields.get_field_name('lmh_rise')
    assert buildings.gdf[height_col].tolist() == [15.0, 25.0]   # HeightDefault + FirstFloor
    assert buildings.gdf[lmh_col].tolist() == ['L', 'L']


def test_building_height_and_lmh_rise_use_class_derived_id():
    """When only EqBldgTypeClass is given (no EqBldgType), building_height/lmh_rise defaults still
    resolve — proving the eq_building_type ID derived from Class cascades to downstream fill blocks."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False, with_eq_bldg_type=False,
                            eq_bldg_type_class=['W1', 'W2'])
    buildings = ttfBuildings(gdf=gdf)
    ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    height_col = buildings.fields.get_field_name('building_height')
    lmh_col = buildings.fields.get_field_name('lmh_rise')
    assert buildings.gdf[height_col].tolist() == [15.0, 25.0]
    assert buildings.gdf[lmh_col].tolist() == ['L', 'L']


def test_area_derived_from_occupancy_type():
    """AreaSqft absent -> derived via eqBuildingArea.csv (Occupancy -> SquareFootage)."""
    gdf = _minimal_ttf_gdf(with_occ=True, with_soccup=False)   # Occupancy_Type = ['RES1', 'RES3A']
    buildings = ttfBuildings(gdf=gdf)
    ttfAALAnalysis(buildings=buildings, vulnerability_func=DefaultTsunamiVulnerability())

    area_col = buildings.fields.get_field_name('area')
    assert buildings.gdf[area_col].tolist() == [1800.0, 2200.0]