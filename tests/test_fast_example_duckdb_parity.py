"""Integration test comparing Python and DuckDB loss pipelines on the fast_analysis example.

Uses the real CSV and TIF files from examples/ to ensure end-to-end parity between the
two calculation paths. With pre-existing DDF IDs preserved in the buildings schema, the
two paths should agree to well within floating-point tolerance (<0.1%).
"""
import duckdb
import pytest
from pathlib import Path

from sphere.core.schemas.fast_buildings import FastBuildings
from sphere.flood.single_value_reader import SingleValueRaster
from sphere.flood.default_vulnerability import DefaultFloodVulnerability
from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
CSV_FILE = EXAMPLES_DIR / "HI_Honolulu_UDF_sample.csv"
TIF_FILE = EXAMPLES_DIR / "Oahu_10_withReef.tif"


@pytest.fixture(scope="module")
def fast_example_results():
    """Run both pipelines once and return (buildings, duckdb_losses)."""
    pytest.importorskip("duckdb")

    buildings = FastBuildings(str(CSV_FILE))
    depth_grid = SingleValueRaster(str(TIF_FILE))
    flood_func = DefaultFloodVulnerability(buildings, flood_type="R")
    analyzer = HazusFloodAnalysis(
        buildings=buildings,
        vulnerability_func=flood_func,
        depth_grid=depth_grid,
    )

    # Python path
    analyzer.calculate_losses()

    # DuckDB path
    conn = duckdb.connect(":memory:")
    try:
        duckdb_losses = analyzer.calculate_losses_duckdb(conn)
    finally:
        conn.close()

    return buildings, duckdb_losses


class TestFastExamplePythonVsDuckDB:
    """Both pipelines on the real fast_analysis example data must agree within 0.1%."""

    def test_flooded_building_count_matches(self, fast_example_results):
        """DuckDB should return losses for the same number of flooded buildings."""
        buildings, duckdb_losses = fast_example_results
        py_flooded = (buildings.building_loss.fillna(0) > 0).sum()
        db_flooded = (duckdb_losses["building_loss"] > 0).sum()
        assert py_flooded == db_flooded, (
            f"Python flooded count {py_flooded} != DuckDB {db_flooded}"
        )

    def test_total_building_loss_within_01_percent(self, fast_example_results):
        """Total building loss must agree between paths to within 0.1%."""
        buildings, duckdb_losses = fast_example_results
        py_total = buildings.building_loss.fillna(0).sum()
        db_total = duckdb_losses["building_loss"].fillna(0).sum()
        assert py_total > 0, "Python building loss is zero — check the example data"
        ratio = abs(db_total - py_total) / py_total
        assert ratio < 0.001, (
            f"Building loss difference {ratio:.4%} exceeds 0.1% tolerance "
            f"(Python ${py_total:,.0f}, DuckDB ${db_total:,.0f})"
        )

    def test_total_content_loss_within_01_percent(self, fast_example_results):
        """Total content loss must agree between paths to within 0.1%."""
        buildings, duckdb_losses = fast_example_results
        py_total = buildings.content_loss.fillna(0).sum()
        db_total = duckdb_losses["content_loss"].fillna(0).sum()
        assert py_total > 0, "Python content loss is zero — check the example data"
        ratio = abs(db_total - py_total) / py_total
        assert ratio < 0.001, (
            f"Content loss difference {ratio:.4%} exceeds 0.1% tolerance "
            f"(Python ${py_total:,.0f}, DuckDB ${db_total:,.0f})"
        )

    def test_per_building_loss_within_01_percent(self, fast_example_results):
        """Per-building building_loss values must agree within 0.1% (median relative error)."""
        import pandas as pd

        buildings, duckdb_losses = fast_example_results
        gdf = buildings.gdf
        id_col = buildings.fields.get_field_name("id")
        bl_col = buildings.fields.get_field_name("building_loss")

        py_df = gdf[[id_col, bl_col]].rename(columns={id_col: "id", bl_col: "py_loss"})
        merged = py_df.merge(
            duckdb_losses[["id", "building_loss"]].rename(columns={"building_loss": "db_loss"}),
            on="id",
            how="inner",
        )
        # Only compare buildings that have a loss in both paths
        flooded = merged[(merged["py_loss"].fillna(0) > 0) & (merged["db_loss"].fillna(0) > 0)]
        assert len(flooded) > 0, "No common flooded buildings found for comparison"

        rel_err = ((flooded["db_loss"] - flooded["py_loss"]).abs() / flooded["py_loss"])
        median_err = rel_err.median()
        assert median_err < 0.001, (
            f"Median per-building relative error {median_err:.4%} exceeds 0.1%"
        )
