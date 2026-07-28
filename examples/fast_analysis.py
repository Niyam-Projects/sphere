import time
from pathlib import Path
import pandas as pd
import duckdb
from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
from sphere.flood.single_value_reader import SingleValueRaster
from sphere.flood.default_vulnerability import DefaultFloodVulnerability
from sphere.core.schemas.fast_buildings import FastBuildings

def run_fast():
    start_time = time.time()  
    # Define file paths (adjust these paths as necessary)
    base_dir = Path(__file__).parent
    buildings_csv = base_dir / "HI_Honolulu_UDF_sample.csv"
    tif_file = base_dir / "Oahu_10_withReef.tif"

    # Load buildings data from CSV
    buildings = FastBuildings(str(buildings_csv))

    # Read the depth grid from the TIFF file
    depth_grid = SingleValueRaster(str(tif_file))

    # Create an instance of the default flood function
    flood_function = DefaultFloodVulnerability(buildings, flood_type="R")

    # Create the Hazus flood analyzer instance.
    analyzer = HazusFloodAnalysis(
        buildings=buildings,
        vulnerability_func=flood_function,
        depth_grid=depth_grid,
    )

    # --- Python path ---
    analyzer.calculate_losses()

    # Save the results to a CSV file
    results_csv = base_dir / "flood_losses.csv"
    buildings.gdf.to_csv(results_csv, index=False)

    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"Execution time: {elapsed_time:.6f} seconds")
    print(f"Flood {len(buildings.gdf):,} analysis complete. Results saved to:", results_csv)

    # --- DuckDB path (file-based so you can inspect intermediate tables) ---
    print("\nRunning DuckDB pipeline for comparison...")
    duckdb_file = base_dir / "fast_analysis.duckdb"
    duckdb_file.unlink(missing_ok=True)  # start fresh each run
    duckdb_start = time.time()
    conn = duckdb.connect(str(duckdb_file))
    try:
        duckdb_losses = analyzer.calculate_losses_duckdb(conn)
    finally:
        conn.close()
    duckdb_elapsed = time.time() - duckdb_start

    py_total = buildings.building_loss.sum()
    ddb_total = duckdb_losses["building_loss"].sum()
    print(f"DuckDB execution time: {duckdb_elapsed:.6f} seconds")
    print(f"DuckDB database saved to: {duckdb_file}")
    print(f"Python  total building loss: ${py_total:,.0f}")
    print(f"DuckDB  total building loss: ${ddb_total:,.0f}")


if __name__ == "__main__":
    run_fast()
