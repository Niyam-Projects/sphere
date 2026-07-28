"""Tests for the DuckDB pipeline in HazusFloodAnalysis2 (updated methodology)."""
import numpy as np
import pandas as pd
import pytest
import duckdb

from sphere.flood.analysis.hazus_flood2 import HazusFloodAnalysis2


class MockFloodDepthGrid:
    def __init__(self, depth: float = 6.0):
        self._depth = depth

    def get_value(self, lon, lat):
        return self._depth

    def get_value_vectorized(self, geometry):
        return np.full(len(geometry), self._depth)


class MockVelocityGrid:
    def __init__(self, velocity: float = 3.0):
        self._velocity = velocity

    def get_value(self, lon, lat):
        return self._velocity

    def get_value_vectorized(self, geometry):
        return np.full(len(geometry), self._velocity)


class MockDurationGrid:
    def __init__(self, duration: float = 48.0):
        self._duration = duration

    def get_value(self, lon, lat):
        return self._duration

    def get_value_vectorized(self, geometry):
        return np.full(len(geometry), self._duration)


@pytest.fixture
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def riverine_analyzer(small_udf_buildings):
    return HazusFloodAnalysis2(
        buildings=small_udf_buildings,
        depth_grid=MockFloodDepthGrid(depth=6.0),
        flood_type="R",
        velocity_grid=MockVelocityGrid(velocity=3.0),
        duration_grid=MockDurationGrid(duration=24.0),
    )


class TestHazusFloodAnalysis2Pipeline:
    """Smoke tests: pipeline runs and output is valid."""

    def test_returns_dataframe(self, riverine_analyzer, duckdb_conn):
        result = riverine_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, riverine_analyzer, duckdb_conn):
        result = riverine_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert {"id", "building_loss", "content_loss", "inventory_loss"}.issubset(result.columns)

    def test_row_count_matches_flooded_buildings(self, small_udf_buildings, duckdb_conn):
        """All buildings flood at depth=6 with FFH=0, so row count == building count."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=6.0),
            flood_type="R",
        )
        result = analyzer.calculate_losses_duckdb(duckdb_conn)
        assert len(result) == len(small_udf_buildings.gdf)

    def test_losses_are_non_negative(self, riverine_analyzer, duckdb_conn):
        result = riverine_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert (result["building_loss"] >= 0).all()
        assert (result["content_loss"] >= 0).all()

    def test_losses_are_finite(self, riverine_analyzer, duckdb_conn):
        result = riverine_analyzer.calculate_losses_duckdb(duckdb_conn)
        assert np.isfinite(result["building_loss"].values).all()


class TestPerilTypeAssignment2:
    """Verify HazusFloodAnalysis2 peril type assignment strategies."""

    def _setup(self, analyzer, conn):
        HazusFloodAnalysis2._setup_spatial_extensions(conn)
        analyzer.buildings.to_duckdb(conn)
        analyzer._create_hazard_table(conn)
        conn.execute("ALTER TABLE buildings ADD COLUMN IF NOT EXISTS flood_peril_type VARCHAR")

    # --- Riverine ---

    def test_riverine_default_assigns_rls(self, small_udf_buildings, duckdb_conn):
        """No vel/dur grids → all riverine buildings get RLS."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.0),
            flood_type="R",
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_riverine_default_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"RLS"}

    def test_riverine_velocity_duration_low_short(self, small_udf_buildings, duckdb_conn):
        """Low velocity + short duration → RLS."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.0),
            flood_type="R",
            velocity_grid=MockVelocityGrid(velocity=2.0),   # < 5 → L
            duration_grid=MockDurationGrid(duration=24.0),  # < 72 → S
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_riverine_velocity_duration_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"RLS"}

    def test_riverine_velocity_duration_high_long(self, small_udf_buildings, duckdb_conn):
        """High velocity + long duration → RHL."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.0),
            flood_type="R",
            velocity_grid=MockVelocityGrid(velocity=6.0),   # >= 5 → H
            duration_grid=MockDurationGrid(duration=96.0),  # >= 72 → L
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_riverine_velocity_duration_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"RHL"}

    def test_riverine_velocity_duration_low_long(self, small_udf_buildings, duckdb_conn):
        """Low velocity + long duration → RLL."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.0),
            flood_type="R",
            velocity_grid=MockVelocityGrid(velocity=2.0),    # L
            duration_grid=MockDurationGrid(duration=100.0),  # L
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_riverine_velocity_duration_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"RLL"}

    def test_riverine_velocity_duration_high_short(self, small_udf_buildings, duckdb_conn):
        """High velocity + short duration → RHS."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.0),
            flood_type="R",
            velocity_grid=MockVelocityGrid(velocity=7.0),   # H
            duration_grid=MockDurationGrid(duration=12.0),  # S
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_riverine_velocity_duration_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"RHS"}

    # --- Coastal ---

    def test_coastal_high_depth_assigns_chw(self, small_udf_buildings, duckdb_conn):
        """depth >= 6 ft → CHW (Coastal High Wave)."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=8.0),
            flood_type="C",
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_coastal_depth_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CHW"}

    def test_coastal_mid_depth_assigns_cmv(self, small_udf_buildings, duckdb_conn):
        """3 <= depth < 6 ft → CMV (Coastal Moderate Wave)."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.5),
            flood_type="C",
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_coastal_depth_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CMV"}

    def test_coastal_low_depth_assigns_cst(self, small_udf_buildings, duckdb_conn):
        """depth < 3 ft → CST (Coastal Stillwater)."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=1.5),
            flood_type="C",
        )
        self._setup(analyzer, duckdb_conn)
        HazusFloodAnalysis2._assign_peril_coastal_depth_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CST"}

    # --- Selector ---

    def test_selector_riverine_uses_velocity_duration(self, small_udf_buildings, duckdb_conn):
        """Selector uses velocity/duration when both grids are provided."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=4.0),
            flood_type="R",
            velocity_grid=MockVelocityGrid(velocity=6.0),   # H
            duration_grid=MockDurationGrid(duration=80.0),  # L
        )
        self._setup(analyzer, duckdb_conn)
        analyzer._assign_flood_peril_type_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"RHL"}

    def test_selector_coastal_uses_depth(self, small_udf_buildings, duckdb_conn):
        """Selector uses depth-based coastal codes when flood_type='C'."""
        analyzer = HazusFloodAnalysis2(
            buildings=small_udf_buildings,
            depth_grid=MockFloodDepthGrid(depth=7.0),
            flood_type="C",
        )
        self._setup(analyzer, duckdb_conn)
        analyzer._assign_flood_peril_type_sql(duckdb_conn)

        peril_types = set(
            duckdb_conn.execute(
                "SELECT DISTINCT flood_peril_type FROM buildings WHERE id IN (SELECT id FROM hazard)"
            ).df()["flood_peril_type"].tolist()
        )
        assert peril_types == {"CHW"}


class TestFoundationNormalization:
    """Verify that Hazus foundation type codes are mapped to 4-word codes."""

    def _build_table(self, conn, codes):
        conn.execute("DROP TABLE IF EXISTS buildings")
        conn.execute("CREATE TABLE buildings (id INTEGER, foundation_type VARCHAR)")
        for i, code in enumerate(codes):
            conn.execute(f"INSERT INTO buildings VALUES ({i}, '{code}')")

    def test_basement_codes(self, duckdb_conn):
        self._build_table(duckdb_conn, ["B", "4", "2"])
        HazusFloodAnalysis2._normalize_foundation_types(duckdb_conn)
        result = duckdb_conn.execute("SELECT DISTINCT foundation_type FROM buildings").df()["foundation_type"].tolist()
        assert set(result) == {"BASEMENT"}

    def test_pile_codes(self, duckdb_conn):
        self._build_table(duckdb_conn, ["W", "P", "I", "C"])
        HazusFloodAnalysis2._normalize_foundation_types(duckdb_conn)
        result = duckdb_conn.execute("SELECT DISTINCT foundation_type FROM buildings").df()["foundation_type"].tolist()
        assert set(result) == {"PILE"}

    def test_shallow_codes(self, duckdb_conn):
        self._build_table(duckdb_conn, ["F", "S", "1"])
        HazusFloodAnalysis2._normalize_foundation_types(duckdb_conn)
        result = duckdb_conn.execute("SELECT DISTINCT foundation_type FROM buildings").df()["foundation_type"].tolist()
        assert set(result) == {"SHALLOW"}

    def test_full_word_codes_unchanged(self, duckdb_conn):
        self._build_table(duckdb_conn, ["BASEMENT", "PILE", "SHALLOW", "SLAB"])
        HazusFloodAnalysis2._normalize_foundation_types(duckdb_conn)
        result = set(
            duckdb_conn.execute("SELECT DISTINCT foundation_type FROM buildings").df()["foundation_type"].tolist()
        )
        assert result == {"BASEMENT", "PILE", "SHALLOW", "SLAB"}


class TestFullPipeline2:
    """End-to-end pipeline runs for both riverine and coastal."""

    def test_riverine_pipeline_runs(self, small_udf_buildings):
        conn = duckdb.connect(":memory:")
        try:
            analyzer = HazusFloodAnalysis2(
                buildings=small_udf_buildings,
                depth_grid=MockFloodDepthGrid(depth=6.0),
                flood_type="R",
                velocity_grid=MockVelocityGrid(velocity=3.0),
                duration_grid=MockDurationGrid(duration=24.0),
            )
            result = analyzer.calculate_losses_duckdb(conn)
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            assert (result["building_loss"] >= 0).all()
        finally:
            conn.close()

    def test_coastal_pipeline_runs(self, small_udf_buildings):
        conn = duckdb.connect(":memory:")
        try:
            analyzer = HazusFloodAnalysis2(
                buildings=small_udf_buildings,
                depth_grid=MockFloodDepthGrid(depth=6.0),
                flood_type="C",
            )
            result = analyzer.calculate_losses_duckdb(conn)
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
            assert (result["building_loss"] >= 0).all()
        finally:
            conn.close()

    def test_riverine_no_grids_falls_back_to_rls(self, small_udf_buildings):
        """Pipeline completes with RLS default when no velocity/duration grids given."""
        conn = duckdb.connect(":memory:")
        try:
            analyzer = HazusFloodAnalysis2(
                buildings=small_udf_buildings,
                depth_grid=MockFloodDepthGrid(depth=6.0),
                flood_type="R",
            )
            result = analyzer.calculate_losses_duckdb(conn)
            assert isinstance(result, pd.DataFrame)
            assert len(result) > 0
        finally:
            conn.close()
