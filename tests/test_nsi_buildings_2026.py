"""Tests for NsiBuildings2026 cost_basis logic (full_replacement vs depreciated)."""
import duckdb
import geopandas as gpd
import pandas as pd
import pytest

from sphere.core.schemas.nsi_buildings_2026 import NsiBuildings2026

# RES1 -> 50%, COM6 -> 150% per hzPctContentofStructureValue.csv
RES1_PCT = 50
COM6_PCT = 150


@pytest.fixture
def nsi2026_parquet(tmp_path):
    """Write a synthetic NSI 2026 geoparquet with the real column names."""
    df = pd.DataFrame(
        {
            "fd_id": [1, 2],
            "occtype": ["RES1-1SNB", "COM6-2SNB"],
            "found_ht": [1.0, 2.0],
            "found_type": ["S", "P"],
            "num_story": [1, 2],
            "sqft": [1000, 2000],
            "val_struct": [100_000, 500_000],
            "val_cont": [50_000, 250_000],
            "fullrep": [150_000, 700_000],
            "bldgtype": ["W1", "S1"],
            "x": [-90.0, -90.1],
            "y": [30.0, 30.1],
        }
    )
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y), crs="EPSG:4326")
    gdf["shape"] = gdf.geometry.to_wkb()
    path = tmp_path / "nsi2026_test.parquet"
    gdf.drop(columns="geometry").to_parquet(path)
    return str(path)


class TestCostBasisValidation:
    def test_invalid_cost_basis_raises(self, nsi2026_parquet):
        with pytest.raises(ValueError):
            NsiBuildings2026(nsi2026_parquet, cost_basis="bogus")


class TestDepreciatedCostBasis:
    """Default mode: building_cost/content_cost pass through val_struct/val_cont."""

    def test_python_path(self, nsi2026_parquet):
        buildings = NsiBuildings2026(nsi2026_parquet, cost_basis="depreciated")
        gdf = buildings.gdf.set_index("fd_id")
        assert gdf.loc[1, "building_cost"] == 100_000
        assert gdf.loc[1, "content_cost"] == 50_000
        assert gdf.loc[2, "building_cost"] == 500_000
        assert gdf.loc[2, "content_cost"] == 250_000

    def test_default_matches_explicit_depreciated(self, nsi2026_parquet):
        """cost_basis defaults to 'depreciated' when omitted."""
        default_buildings = NsiBuildings2026(nsi2026_parquet)
        explicit_buildings = NsiBuildings2026(nsi2026_parquet, cost_basis="depreciated")
        pd.testing.assert_series_equal(
            default_buildings.gdf["building_cost"].sort_values().reset_index(drop=True),
            explicit_buildings.gdf["building_cost"].sort_values().reset_index(drop=True),
        )

    def test_duckdb_path(self, nsi2026_parquet):
        buildings = NsiBuildings2026(nsi2026_parquet, cost_basis="depreciated")
        conn = duckdb.connect(":memory:")
        try:
            buildings.to_duckdb(conn)
            result = conn.execute(
                "SELECT id, building_cost, content_cost FROM buildings ORDER BY id"
            ).df()
        finally:
            conn.close()
        assert result.loc[result["id"] == 1, "building_cost"].iloc[0] == 100_000
        assert result.loc[result["id"] == 1, "content_cost"].iloc[0] == 50_000
        assert result.loc[result["id"] == 2, "building_cost"].iloc[0] == 500_000
        assert result.loc[result["id"] == 2, "content_cost"].iloc[0] == 250_000


class TestFullReplacementCostBasis:
    """building_cost = fullrep; content_cost = fullrep * hzPctContentofStructureValue / 100."""

    def test_python_path(self, nsi2026_parquet):
        buildings = NsiBuildings2026(nsi2026_parquet, cost_basis="full_replacement")
        gdf = buildings.gdf.set_index("fd_id")

        assert gdf.loc[1, "building_cost"] == 150_000
        assert gdf.loc[1, "content_cost"] == pytest.approx(150_000 * RES1_PCT / 100.0)

        assert gdf.loc[2, "building_cost"] == 700_000
        assert gdf.loc[2, "content_cost"] == pytest.approx(700_000 * COM6_PCT / 100.0)

    def test_duckdb_path(self, nsi2026_parquet):
        buildings = NsiBuildings2026(nsi2026_parquet, cost_basis="full_replacement")
        conn = duckdb.connect(":memory:")
        try:
            buildings.to_duckdb(conn)
            result = conn.execute(
                "SELECT id, building_cost, content_cost FROM buildings ORDER BY id"
            ).df()
        finally:
            conn.close()

        row1 = result.loc[result["id"] == 1].iloc[0]
        assert row1["building_cost"] == 150_000
        assert row1["content_cost"] == pytest.approx(150_000 * RES1_PCT / 100.0)

        row2 = result.loc[result["id"] == 2].iloc[0]
        assert row2["building_cost"] == 700_000
        assert row2["content_cost"] == pytest.approx(700_000 * COM6_PCT / 100.0)

    def test_python_and_duckdb_paths_agree(self, nsi2026_parquet):
        """Both loading paths must derive identical costs from the same cost_basis."""
        buildings = NsiBuildings2026(nsi2026_parquet, cost_basis="full_replacement")
        python_costs = (
            buildings.gdf.set_index("fd_id")[["building_cost", "content_cost"]]
            .sort_index()
        )

        conn = duckdb.connect(":memory:")
        try:
            buildings.to_duckdb(conn)
            duckdb_costs = (
                conn.execute("SELECT id, building_cost, content_cost FROM buildings")
                .df()
                .set_index("id")
                .sort_index()
            )
        finally:
            conn.close()

        pd.testing.assert_series_equal(
            python_costs["building_cost"], duckdb_costs["building_cost"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            python_costs["content_cost"], duckdb_costs["content_cost"],
            check_names=False,
        )
