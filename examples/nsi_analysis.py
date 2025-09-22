import time
from pathlib import Path
import pandas as pd
import urllib.request
import zipfile
from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
from sphere.flood.single_value_reader import SingleValueRaster
from sphere.flood.default_vulnerability import DefaultFloodVulnerability
from sphere.core.schemas.nsi_buildings import NsiBuildings

def ensure_nsi_gpkg(base_dir: Path, state_fips: int) -> Path:
    """Ensure the NSI geopackage for `state_fips` exists in `base_dir`.
    If the .gpkg already exists, return it. Otherwise download the zip and extract.
    Returns the Path to the geopackage file.
    """
    expected_name = f"nsi_2022_{state_fips}.gpkg"
    expected_path = base_dir / expected_name

    # If the exact expected gpkg exists, return it (skip download/extract)
    if expected_path.exists():
        print(f"Found existing geopackage {expected_path}, skipping download/extract.")
        return expected_path

    # If any gpkg containing the fips code exists, use that
    gpkg_matches = list(base_dir.glob(f"*{state_fips}*.gpkg"))
    if gpkg_matches:
        print(f"Found existing geopackage(s) {gpkg_matches}, using {gpkg_matches[0]}")
        return gpkg_matches[0]

    # Otherwise download and extract
    remote_zip_url = f"https://nsi.sec.usace.army.mil/downloads/nsi_2022/nsi_2022_{state_fips}.gpkg.zip"
    zip_name = remote_zip_url.split('/')[-1]
    zip_path = base_dir / zip_name

    if not zip_path.exists():
        print(f"Downloading {remote_zip_url} to {zip_path}...")
        try:
            urllib.request.urlretrieve(remote_zip_url, str(zip_path))
        except Exception as e:
            raise RuntimeError(f"Failed to download {remote_zip_url}: {e}")
        print("Download complete.")
    else:
        print(f"Zip already exists at {zip_path}, skipping download.")

    # Extract the zip into the script folder
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            print(f"Extracting {zip_path} to {base_dir}...")
            zf.extractall(path=str(base_dir))
    except zipfile.BadZipFile:
        raise RuntimeError(f"Downloaded file at {zip_path} is not a valid zip archive")

    # Locate the extracted geopackage file (look for .gpkg in the folder)
    gpkg_files = list(base_dir.glob(f"*{state_fips}*.gpkg")) or list(base_dir.glob("*.gpkg"))
    if not gpkg_files:
        raise FileNotFoundError(f"No .gpkg file found in {base_dir} after extracting {zip_path}")

    # Prefer one that contains the fips code in the name if available
    selected = gpkg_files[0]
    for p in gpkg_files:
        if str(state_fips) in p.name:
            selected = p
            break

    return selected

def run_nsi_flood(state_fips: int):
    start_time = time.time()  
    # Define file paths (adjust these paths as necessary)
    base_dir = Path(__file__).parent
    tif_file = base_dir / "Oahu_10_withReef.tif"

    # Ensure the geopackage exists (download/extract only if needed)
    nsi_gpkg = ensure_nsi_gpkg(base_dir, state_fips)

    # Load buildings data from the geopackage
    buildings = NsiBuildings(str(nsi_gpkg))

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

    # Save the results to a Parquet file
    results_file = base_dir / f"sphere_results_{state_fips}.parquet"
    buildings.gdf.to_parquet(results_file, compression='zstd')

    end_time = time.time()                 # Record the end time
    elapsed_time = end_time - start_time   # Calculate the time difference
    
    print(f"Execution time: {elapsed_time:.6f} seconds")
    print(f"Flood {len(buildings.gdf):,} analysis complete. Results saved to:", results_file)


if __name__ == "__main__":
    run_nsi_flood(15)