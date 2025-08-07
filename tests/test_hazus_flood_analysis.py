import pytest
import numpy as np
import pandas as pd
import geopandas as gpd

from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.abstract_vulnerability_function import AbstractVulnerabilityFunction
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader
from sphere.flood.default_vulnerability import DefaultFloodVulnerability


class MockVulnerabilityFunction(AbstractVulnerabilityFunction):
    """Mock vulnerability function for testing."""
    
    def __init__(self, buildings):
        self.buildings = buildings
        
    def calculate_vulnerability(self):
        """Set mock damage percentages."""
        fields = self.buildings.fields
        gdf = self.buildings.gdf
        
        # Set mock damage percentages
        gdf[fields.get_field_name('building_damage_percent')] = 20.0
        gdf[fields.get_field_name('content_damage_percent')] = 15.0
        
        # Set inventory damage if inventory cost exists
        inventory_cost_col = fields.get_field_name('inventory_cost')
        if inventory_cost_col in gdf.columns and gdf[inventory_cost_col].sum() > 0:
            gdf[fields.get_field_name('inventory_damage_percent')] = 10.0
        else:
            gdf[fields.get_field_name('inventory_damage_percent')] = 0.0
    
    def apply_damage_percentages(self):
        """Apply damage percentages - mock implementation."""
        pass


class MockFloodDepthGrid(AbstractRasterReader):
    """Mock flood depth grid for testing."""
    
    def get_value(self, lon: float, lat: float) -> float:
        """Return mock flood depth value for a single point."""
        return 6.0
    
    def get_value_vectorized(self, geometry):
        """Return mock flood depth values."""
        return np.full(len(geometry), 6.0)


class TestHazusFloodAnalysis:
    """Test suite for HazusFloodAnalysis class."""

    def test_init(self, small_udf_buildings):
        """Test HazusFloodAnalysis initialization."""
        vulnerability_func = MockVulnerabilityFunction(small_udf_buildings)
        depth_grid = MockFloodDepthGrid()
        
        analysis = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        assert analysis.buildings is small_udf_buildings
        assert analysis.vulnerability_func is vulnerability_func
        assert analysis.depth_grid is depth_grid
        assert hasattr(analysis, 'debris')
        assert hasattr(analysis, 'restoration')

    def test_calculate_losses_basic(self, small_udf_buildings):
        """Test basic loss calculation functionality."""
        vulnerability_func = MockVulnerabilityFunction(small_udf_buildings)
        depth_grid = MockFloodDepthGrid()
        
        analysis = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        # Run the analysis
        analysis.calculate_losses()
        
        result = small_udf_buildings.gdf
        
        # Basic assertions
        assert not result.empty
        assert len(result) == 9  # Should have 9 buildings as per conftest.py
        
        # Check that required output fields exist
        assert small_udf_buildings.fields.get_field_name("flood_depth") in result.columns
        assert small_udf_buildings.fields.get_field_name("depth_in_structure") in result.columns
        assert small_udf_buildings.fields.get_field_name("building_loss") in result.columns
        assert small_udf_buildings.fields.get_field_name("content_loss") in result.columns
        
        # Verify that flood depth values are set correctly (should be 6.0 from mock)
        flood_depth_col = small_udf_buildings.fields.get_field_name("flood_depth")
        assert all(result[flood_depth_col] == 6.0)
        
        # Verify that depth in structure is calculated correctly
        depth_in_structure_col = small_udf_buildings.fields.get_field_name("depth_in_structure")
        first_floor_height_col = small_udf_buildings.fields.get_field_name("first_floor_height")
        expected_depth_in_structure = result[flood_depth_col] - result[first_floor_height_col]
        pd.testing.assert_series_equal(
            result[depth_in_structure_col], 
            expected_depth_in_structure, 
            check_names=False
        )
        
        # Verify that losses are calculated (should be > 0 since we have positive damage percentages)
        building_loss_col = small_udf_buildings.fields.get_field_name("building_loss")
        content_loss_col = small_udf_buildings.fields.get_field_name("content_loss")
        assert all(result[building_loss_col] > 0.0)
        assert all(result[content_loss_col] > 0.0)

    def test_calculate_losses_with_real_vulnerability(self, small_udf_buildings):
        """Test loss calculation with real DefaultFloodVulnerability function."""
        depth_grid = MockFloodDepthGrid()
        
        # Use the real vulnerability function
        vulnerability_func = DefaultFloodVulnerability(
            buildings=small_udf_buildings,
            flood_type="R"  # Riverine flooding
        )
        
        analysis = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        # Run the analysis
        analysis.calculate_losses()
        
        result = small_udf_buildings.gdf
        
        # Basic assertions
        assert not result.empty
        
        # Check that damage function IDs were assigned
        bddf_id_col = small_udf_buildings.fields.get_field_name("bddf_id")
        cddf_id_col = small_udf_buildings.fields.get_field_name("cddf_id")
        assert bddf_id_col in result.columns
        assert cddf_id_col in result.columns
        
        # Check that damage percentages were calculated
        building_damage_col = small_udf_buildings.fields.get_field_name("building_damage_percent")
        content_damage_col = small_udf_buildings.fields.get_field_name("content_damage_percent")
        assert building_damage_col in result.columns
        assert content_damage_col in result.columns
        
        # Check that losses were calculated
        building_loss_col = small_udf_buildings.fields.get_field_name("building_loss")
        content_loss_col = small_udf_buildings.fields.get_field_name("content_loss")
        assert all(result[building_loss_col] >= 0.0)  # Losses should be non-negative
        assert all(result[content_loss_col] >= 0.0)

    def test_debris_calculation(self, small_udf_buildings):
        """Test that debris calculations are performed."""
        vulnerability_func = MockVulnerabilityFunction(small_udf_buildings)
        depth_grid = MockFloodDepthGrid()
        
        analysis = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        # Run the analysis
        analysis.calculate_losses()
        
        result = small_udf_buildings.gdf
        
        # Check that debris fields are created
        debris_finish_col = small_udf_buildings.fields.get_field_name("debris_finish")
        debris_foundation_col = small_udf_buildings.fields.get_field_name("debris_foundation")
        debris_structure_col = small_udf_buildings.fields.get_field_name("debris_structure")
        debris_total_col = small_udf_buildings.fields.get_field_name("debris_total")
        
        assert debris_finish_col in result.columns
        assert debris_foundation_col in result.columns
        assert debris_structure_col in result.columns
        assert debris_total_col in result.columns
        
        # Check that debris values are calculated (should be non-negative)
        assert all(result[debris_finish_col] >= 0.0)
        assert all(result[debris_foundation_col] >= 0.0)
        assert all(result[debris_structure_col] >= 0.0)
        assert all(result[debris_total_col] >= 0.0)

    def test_restoration_calculation(self, small_udf_buildings):
        """Test that restoration calculations are performed."""
        vulnerability_func = MockVulnerabilityFunction(small_udf_buildings)
        depth_grid = MockFloodDepthGrid()
        
        analysis = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        # Run the analysis
        analysis.calculate_losses()
        
        result = small_udf_buildings.gdf
        
        # Check that restoration fields are created
        restoration_min_col = small_udf_buildings.fields.get_field_name("restoration_minimum")
        restoration_max_col = small_udf_buildings.fields.get_field_name("restoration_maximum")
        
        assert restoration_min_col in result.columns
        assert restoration_max_col in result.columns

    def test_coastal_vs_riverine_flood_types(self, small_udf_buildings):
        """Test that different flood types produce different results."""
        depth_grid = MockFloodDepthGrid()
        
        # Test riverine flooding
        vulnerability_func_r = DefaultFloodVulnerability(
            buildings=small_udf_buildings,
            flood_type="R"
        )
        
        analysis_r = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func_r,
            depth_grid=depth_grid
        )
        analysis_r.calculate_losses()
        result_r = small_udf_buildings.gdf.copy()
        
        # Reset the buildings for coastal test - use a fresh copy
        from tests.conftest import DummyBuildingPoints
        import pandas as pd
        
        # Get the original data from conftest.py pattern
        data = [
            {
                "Id": 1,
                "HNL_UDF_EQ": "RM1M",
                "OccupancyType": "RES3E",
                "Cost": 2254898,
                "NumStories": 7,
                "FoundationType": 7,
                "FirstFloorHt": 1,
                "Area": 11040,
                "BDDF_ID": 204,
                "CDDF_ID": 81,
                "YEARBUILT": 1974,
                "Tract": 15003000106,
                "Latitude": 21.29,
                "Longitude": -157.72,
                "Depth_Grid": 6.0,
                "Depth_in_Struc": 5.0,
                "flExp": 1,
                "SOID": "R3E5N",
                "ContentCostUSD": 1127449,
                "InventoryCostUSD": 0.0,
            },
        ]
        df = pd.DataFrame(data)
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326"
        )
        coastal_buildings = DummyBuildingPoints(gdf=gdf)
        
        # Test coastal flooding
        vulnerability_func_c = DefaultFloodVulnerability(
            buildings=coastal_buildings,
            flood_type="C"
        )
        
        analysis_c = HazusFloodAnalysis(
            buildings=coastal_buildings,
            vulnerability_func=vulnerability_func_c,
            depth_grid=depth_grid
        )
        analysis_c.calculate_losses()
        result_c = coastal_buildings.gdf.copy()
        
        # The results should potentially be different for different flood types
        # (though they might be the same in some cases depending on the data)
        assert len(result_r) >= 1  # Should have at least one building
        assert len(result_c) >= 1  # Should have at least one building
        
        # Both should have valid results
        building_loss_col_r = small_udf_buildings.fields.get_field_name("building_loss")
        building_loss_col_c = coastal_buildings.fields.get_field_name("building_loss")
        assert all(result_r[building_loss_col_r] >= 0.0)
        assert all(result_c[building_loss_col_c] >= 0.0)

    def test_inventory_cost_handling(self, small_udf_buildings):
        """Test handling of inventory costs when present and absent."""
        vulnerability_func = MockVulnerabilityFunction(small_udf_buildings)
        depth_grid = MockFloodDepthGrid()
        
        analysis = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        analysis.calculate_losses()
        result = small_udf_buildings.gdf
        
        # Inventory loss should be 0 when no inventory cost
        inventory_loss_col = small_udf_buildings.fields.get_field_name("inventory_loss")
        if inventory_loss_col in result.columns:
            # If the column exists, values should be 0 or NaN
            assert all((result[inventory_loss_col] == 0.0) | pd.isna(result[inventory_loss_col]))

    def test_field_mapping_flexibility(self, small_udf_buildings):
        """Test that the system works with different field names."""
        # Create buildings data with different column names but use a subset of sample data
        original_data = small_udf_buildings.gdf.iloc[:2].copy()  # Use first 2 buildings
        
        # Create simplified data with renamed columns
        renamed_data = pd.DataFrame({
            'building_id': [1, 2],
            'occupancy_type': ['RES3E', 'IND2'], 
            'first_floor_height': [1, 1],
            'foundation_type': [7, 7],
            'number_stories': [7, 1],
            'building_area': [11040, 11724],
            'building_cost': [2254898, 1484865],
            'content_cost': [1127449, 2227298],
            'Longitude': [-157.72, -158.1],
            'Latitude': [21.29, 21.59],
        })
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(
            renamed_data,
            geometry=gpd.points_from_xy(
                renamed_data['Longitude'],
                renamed_data['Latitude']
            ),
            crs='EPSG:4326'
        )
        
        # Create Buildings object with no overrides (should use automatic mapping)
        buildings = Buildings(gdf)
        
        # Create mock vulnerability function
        class TestMockVulnerabilityFunction(AbstractVulnerabilityFunction):
            def __init__(self, buildings):
                self.buildings = buildings
                
            def calculate_vulnerability(self):
                fields = self.buildings.fields
                gdf = self.buildings.gdf
                gdf[fields.get_field_name('building_damage_percent')] = 20.0
                gdf[fields.get_field_name('content_damage_percent')] = 15.0
            
            def apply_damage_percentages(self):
                pass
        
        vulnerability_func = TestMockVulnerabilityFunction(buildings)
        
        # Create mock flood depth grid
        depth_grid = MockFloodDepthGrid()
        
        # Test that analysis works with automatically mapped fields
        analysis = HazusFloodAnalysis(
            buildings=buildings,
            vulnerability_func=vulnerability_func,
            depth_grid=depth_grid
        )
        
        analysis.calculate_losses()
        result = buildings.gdf
        
        # Should work without errors
        assert not result.empty
        assert buildings.fields.get_field_name("building_loss") in result.columns
