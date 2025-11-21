import pytest
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point

from sphere.core.schemas.buildings import Buildings
from sphere.tsunami.analysis.hazus_tsunami import HazusTsunamiAnalysis
from sphere.tsunami.default_vulnerability import DefaultTsunamiVulnerability
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader


class MockRasterReader(AbstractRasterReader):
    """Mock raster reader that returns the values from the CSV."""
    
    def __init__(self, values: pd.Series):
        """Initialize with a pandas Series of values."""
        self.values = values.values
    
    def get_value(self, lon: float, lat: float) -> float:
        return self.values[0]  # Not used in this test

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
def mock_rasters(nsi_buildings_data):
    """Create mock raster readers using the CSV data."""
    _, _, depth_values, flux_values = nsi_buildings_data
    
    depth_raster = MockRasterReader(depth_values)
    flux_raster = MockRasterReader(flux_values)
    
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
    
    computed_building_loss = result_df[buildings.fields.building_loss].values
    pd.testing.assert_allclose(
        computed_building_loss,
        expected_losses['BldgLossUSD'],
        rtol=rtol,
        err_msg="Building loss values don't match expected"
    )
    
    computed_content_loss = result_df[buildings.fields.content_loss].values
    pd.testing.assert_allclose(
        computed_content_loss,
        expected_losses['ContentLossUSD'],
        rtol=rtol,
        err_msg="Content loss values don't match expected"
    )
    
    computed_relocation_loss = result_df[buildings.fields.relocation_loss].values
    pd.testing.assert_allclose(
        computed_relocation_loss,
        expected_losses['RelocationLossUSD'],
        rtol=rtol,
        err_msg="Relocation loss values don't match expected"
    )
    
    computed_income_loss = result_df[buildings.fields.income_loss].values
    pd.testing.assert_allclose(
        computed_income_loss,
        expected_losses['IncomeLossUSD'],
        rtol=rtol,
        err_msg="Income loss values don't match expected"
    )
    
    computed_rental_loss = result_df[buildings.fields.rental_loss].values
    pd.testing.assert_allclose(
        computed_rental_loss,
        expected_losses['RentalLossUSD'],
        rtol=rtol,
        err_msg="Rental loss values don't match expected"
    )
    
    computed_wage_loss = result_df[buildings.fields.wage_loss].values
    pd.testing.assert_allclose(
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
    assert buildings.fields.building_loss in result_df.columns
    assert buildings.fields.content_loss in result_df.columns
    assert buildings.fields.relocation_loss in result_df.columns
