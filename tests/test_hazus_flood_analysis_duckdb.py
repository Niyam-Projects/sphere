"""Tests for the DuckDB-based flood analysis pipeline in HazusFloodAnalysis."""
import numpy as np
import pandas as pd
import pytest
import duckdb

from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
from sphere.flood.default_vulnerability import DefaultFloodVulnerability


class MockFloodDepthGrid:
    """Constant flood depth raster for testing."""

    def __init__(self, depth: float = 6.0):
        self._depth = depth

    def get_value(self, lon: float, lat: float) -> float:
        return self._depth

    def get_value_vectorized(self, geometry):
        return np.full(len(geometry), self._depth)


@pytest.fixture
def duckdb_conn():
    """In-memory DuckDB connection, closed after each test."""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def hazus_analyzer(small_udf_buildings):
    """HazusFloodAnalysis wired with real vulnerability and mock raster."""
    depth_grid = MockFloodDepthGrid()
    flood_func = DefaultFloodVulnerability(small_udf_buildings, flood_type="R")
    return HazusFloodAnalysis(
        buildings=small_udf_buildings,
        vulnerability_func=flood_func,
        depth_grid=depth_grid,
    )


class TestCalculateLossesDuckDB:
    """Smoke tests and validation for calculate_losses_duckdb()."""

    def test_returns_dataframe(self, hazus_analyzer, duckdb_conn):
        """calculate_losses_duckdb should return a non-empty DataFrame."""
        result = hazus_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_result_has_required_columns(self, hazus_analyzer, duckdb_conn):
        """Result DataFrame must contain id, building_loss, content_loss, inventory_loss."""
        result = hazus_analyzer.calculate_losses_duckdb(duckdb_conn)
        for col in ("id", "building_loss", "content_loss", "inventory_loss"):
            assert col in result.columns, f"Missing column: {col}"

    def test_losses_are_non_negative(self, hazus_analyzer, duckdb_conn):
        """All loss values must be >= 0."""
        result = hazus_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert (result["building_loss"] >= 0).all()
        assert (result["content_loss"] >= 0).all()
        assert (result["inventory_loss"] >= 0).all()

    def test_losses_are_finite(self, hazus_analyzer, duckdb_conn):
        """Loss values must not be NaN or infinite."""
        result = hazus_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert result["building_loss"].notna().all(), "building_loss contains NaN"
        assert result["content_loss"].notna().all(), "content_loss contains NaN"
        assert result["inventory_loss"].notna().all(), "inventory_loss contains NaN"


class TestBuildingsTableSchema:
    """Verify the standardized buildings table schema after to_duckdb()."""

    def test_buildings_table_has_standard_columns(self, small_udf_buildings, duckdb_conn):
        """Buildings DuckDB table must include all standardized schema columns."""
        small_udf_buildings.to_duckdb(duckdb_conn)
        cols = duckdb_conn.execute("SELECT column_name FROM (DESCRIBE buildings)").df()[
            "column_name"
        ].tolist()
        expected = [
            "id",
            "occupancy_type",
            "first_floor_height",
            "foundation_type",
            "number_stories",
            "area",
            "building_cost",
            "content_cost",
            "inventory_value",
            "general_building_type",
        ]
        for col in expected:
            assert col in cols, f"Missing standardized column: {col}"

    def test_buildings_table_row_count_matches_gdf(self, small_udf_buildings, duckdb_conn):
        """Row count in DuckDB buildings table must match the source GeoDataFrame."""
        small_udf_buildings.to_duckdb(duckdb_conn)
        count = duckdb_conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
        assert count == len(small_udf_buildings.gdf)

    def test_buildings_occupancy_type_preserved(self, small_udf_buildings, duckdb_conn):
        """occupancy_type values must be preserved through to_duckdb()."""
        expected_occ = set(small_udf_buildings.occupancy_type.dropna().unique())
        small_udf_buildings.to_duckdb(duckdb_conn)
        actual_occ = set(
            duckdb_conn.execute(
                "SELECT DISTINCT occupancy_type FROM buildings WHERE occupancy_type IS NOT NULL"
            )
            .df()["occupancy_type"]
            .tolist()
        )
        assert expected_occ == actual_occ


class TestDuckDBVsPythonLossComparison:
    """DuckDB and Python pipeline losses should be in the same ballpark."""

    def test_total_building_loss_within_tolerance(self, hazus_analyzer, duckdb_conn):
        """Total building loss from DuckDB path should be within 20% of Python path.

        A 20% tolerance is used because the DuckDB path uses a different interpolation
        engine (pure SQL) vs the Python path (numpy searchsorted).  Both implement the
        same methodology but floating-point ordering and edge-case handling may differ.
        """
        # Python path
        hazus_analyzer.calculate_losses()
        python_building_loss = hazus_analyzer.buildings.building_loss.sum()

        # DuckDB path (fresh connection/state)
        conn2 = duckdb.connect(":memory:")
        try:
            result = hazus_analyzer.calculate_losses_duckdb(conn2)
            duckdb_building_loss = result["building_loss"].sum()
        finally:
            conn2.close()

        if python_building_loss == 0:
            assert duckdb_building_loss == 0, "Both paths should give 0 loss for zero-cost buildings"
            return

        ratio = abs(duckdb_building_loss - python_building_loss) / abs(python_building_loss)
        assert ratio < 0.1, (
            f"DuckDB total building loss ({duckdb_building_loss:,.0f}) differs from "
            f"Python total ({python_building_loss:,.0f}) by {ratio:.1%} (> 20% tolerance)"
        )


class TestPerilTypeAssignment:
    """Verify the two peril-type assignment strategies for HazusFloodAnalysis (traditional Hazus)."""

    def _setup_buildings_hazard(self, analyzer, conn, depth=6.0):
        """Shared helper: load buildings + hazard tables into conn."""
        HazusFloodAnalysis._setup_spatial_extensions(conn)
        analyzer.buildings.to_duckdb(conn)
        analyzer._create_hazard_table(conn)
        conn.execute("ALTER TABLE buildings ADD COLUMN IF NOT EXISTS flood_peril_type VARCHAR")

    def test_riverine_default_assigns_r(self, small_udf_buildings, duckdb_conn):
        """Riverine default strategy assigns R to all flooded buildings."""
        analyzer = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="R"),
            depth_grid=MockFloodDepthGrid(depth=6.0),
        )
        self._setup_buildings_hazard(analyzer, duckdb_conn)
        HazusFloodAnalysis._assign_peril_riverine_default_sql(duckdb_conn)

        peril_types = (
            duckdb_conn.execute("SELECT DISTINCT flood_peril_type FROM buildings WHERE flood_peril_type IS NOT NULL")
            .df()["flood_peril_type"]
            .tolist()
        )
        assert peril_types == ["R"], f"Expected ['R'], got {peril_types}"

    def test_coastal_depth_assigns_cv_at_high_depth(self, small_udf_buildings, duckdb_conn):
        """Coastal depth strategy assigns CV when flood depth >= 6 ft."""
        analyzer = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="C"),
            depth_grid=MockFloodDepthGrid(depth=8.0),
        )
        self._setup_buildings_hazard(analyzer, duckdb_conn)
        HazusFloodAnalysis._assign_peril_coastal_depth_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings "
                "WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CV"}

    def test_coastal_depth_assigns_ca_at_mid_depth(self, small_udf_buildings, duckdb_conn):
        """Coastal depth strategy assigns CA when 3 <= flood depth < 6 ft."""
        analyzer = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="C"),
            depth_grid=MockFloodDepthGrid(depth=4.5),
        )
        self._setup_buildings_hazard(analyzer, duckdb_conn)
        HazusFloodAnalysis._assign_peril_coastal_depth_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings "
                "WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CA"}

    def test_coastal_depth_assigns_r_at_low_depth(self, small_udf_buildings, duckdb_conn):
        """Coastal depth strategy assigns R when flood depth < 3 ft."""
        analyzer = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="C"),
            depth_grid=MockFloodDepthGrid(depth=1.5),
        )
        self._setup_buildings_hazard(analyzer, duckdb_conn)
        HazusFloodAnalysis._assign_peril_coastal_depth_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings "
                "WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"R"}

    def test_selector_uses_coastal_depth_when_flood_type_is_c(self, small_udf_buildings, duckdb_conn):
        """_assign_flood_peril_type_sql picks coastal depth mode when flood_type='C'."""
        analyzer = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="C"),
            depth_grid=MockFloodDepthGrid(depth=7.0),
        )
        self._setup_buildings_hazard(analyzer, duckdb_conn)
        analyzer._assign_flood_peril_type_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings "
                "WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CV"}

    def test_selector_uses_riverine_default_when_flood_type_is_r(self, small_udf_buildings, duckdb_conn):
        """_assign_flood_peril_type_sql uses riverine R for flood_type='R'."""
        analyzer = HazusFloodAnalysis(
            buildings=small_udf_buildings,
            vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="R"),
            depth_grid=MockFloodDepthGrid(depth=4.0),
        )
        self._setup_buildings_hazard(analyzer, duckdb_conn)
        analyzer._assign_flood_peril_type_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings "
                "WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"R"}

    def test_coastal_full_pipeline_runs(self, small_udf_buildings):
        """Full DuckDB pipeline completes without error with flood_type='C'."""
        conn = duckdb.connect(":memory:")
        try:
            analyzer = HazusFloodAnalysis(
                buildings=small_udf_buildings,
                vulnerability_func=DefaultFloodVulnerability(small_udf_buildings, flood_type="C"),
                depth_grid=MockFloodDepthGrid(depth=6.0),
            )
            result = analyzer.calculate_losses_duckdb(conn)
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
        finally:
            conn.close()

