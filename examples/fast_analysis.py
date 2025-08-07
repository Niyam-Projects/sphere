import time
from pathlib import Path
import pandas as pd
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
    # (Assumes that HazusFloodAnalyzer accepts buildings DataFrame, depth grid, the flood function,
    # and geospatial metadata like transform and crs.)
    analyzer = HazusFloodAnalysis(
        buildings=buildings,
        vulnerability_func=flood_function,
        depth_grid=depth_grid,
    )

    # Calculate losses using the analysis
    analyzer.calculate_losses()  # Expected to return a DataFrame

    # Save the results to a CSV file
    results_csv = base_dir / "flood_losses.csv"
    buildings.gdf.to_csv(results_csv, index=False)

    end_time = time.time()                 # Record the end time
    elapsed_time = end_time - start_time   # Calculate the time difference
    
    print(f"Execution time: {elapsed_time:.6f} seconds")
    print(f"Flood {len(buildings.gdf):,} analysis complete. Results saved to:", results_csv)


if __name__ == "__main__":
    run_fast()