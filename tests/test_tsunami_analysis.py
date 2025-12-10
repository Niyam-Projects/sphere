import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point

from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.buildings import ttfBuildings
from sphere.tsunami.analysis.hazus_tsunami import HazusTsunamiAnalysis
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
    csv_path = Path(__file__).parent / "data" / "Oahu_Output_TTF_Hazus_Extended_wArea.csv"
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
    print("Flood return list:", flood_return_list)
    depth_values = df[flood_return_list]
    print("Flux return list:", flux_return_list)
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
    result_df.to_csv("ttf_result_losses.csv") # This file is quite large!
    
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