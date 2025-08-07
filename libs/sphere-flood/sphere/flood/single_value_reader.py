import numpy as np
import geopandas as gpd
import rasterio
import time
from sphere.core.schemas.abstract_raster_reader import AbstractRasterReader

class SingleValueRaster(AbstractRasterReader):
    def __init__(self, data_source: str, crs: str = "EPSG:4326"):
        """
        Initializes a SingleValueRaster object for reading single-value raster data.

        Args:
            data_source (str): Path to the raster file.
        """
        self.data_source = data_source
        self.data = rasterio.open(self.data_source)

        # Check if CRS is None or empty and assign default if needed
        if not self.data.crs:
            # We can't modify the CRS of an opened rasterio dataset directly
            # Instead, store the default CRS as a property to use in methods
            self._default_crs = crs
            print(f"Warning: Raster has no CRS. Using default: {crs}")
        else:
            self._default_crs = None

    def get_value(self, lon: float, lat: float) -> float:
        """
        Extracts flood depth value at a given location.

        Args:
            lon (float): Longitude.
            lat (float): Latitude.

        Returns:
            float: Flood depth value.
        """
        # Check if the point is within the raster bounds.  Important for efficiency and correctness.
        if not (self.data.bounds.left <= lon <= self.data.bounds.right and
                self.data.bounds.bottom <= lat <= self.data.bounds.top):
            raise ValueError(f"Coordinates ({lon}, {lat}) are outside raster bounds.")
        
        # Use sample to efficiently extract the value.
        try:
            for val in self.data.sample([(lon, lat)], indexes=1):  # Specify indexes=1 to get band 1
                # Check for NoData value.  Crucially, use the dataset's nodata value.
                if val[0] == self.data.nodata:
                    return np.nan  # Return NaN for NoData
                else:
                    return float(val[0])  # Convert to float (important if it's a numpy type)
            
            # If sample() doesn't yield any values (empty iterator)
            return np.nan
        except rasterio.RasterioIOError as e:
            # Handle cases where the sample might fail (e.g., out of bounds).
            raise ValueError(f"Could not extract flood depth at ({lon}, {lat}): {e}")

    def get_value_vectorized(self, geometry: gpd.GeoSeries) -> np.ndarray:
        """
        Extracts flood depth for multiple locations in a vectorized way, handling NoData.

        Args:
            geometry (GeoSeries): A GeoSeries of Point geometries (EPSG:4326).

        Returns:
            np.ndarray: Array of flood depth values (float). Returns np.nan for NoData or out-of-bounds points.

        Raises:
            TypeError: If `geometry` is not a GeoSeries or if self.data is not a rasterio DatasetReader.
        """
        start_time = time.time()
        
        if not isinstance(self.data, rasterio.DatasetReader):
            raise TypeError("self.data must be a rasterio.DatasetReader object.")

        if not isinstance(geometry, gpd.GeoSeries):
            raise TypeError("geometry must be a GeoSeries.")

        # Ensure the GeoSeries has a CRS set
        if geometry.crs is None:
            raise ValueError("GeoSeries must have a CRS set.")
        
        # Time CRS reprojection if needed
        reproject_start = time.time()

        # If raster has a CRS, reproject if necessary
        if (geometry.crs != self.data.crs) and (self.data.crs is not None):
            geometry = geometry.to_crs(self.data.crs)
            print(f"CRS reprojection took {time.time() - reproject_start:.6f} seconds")
        elif self._default_crs:
            # If raster has no CRS but we have a default, assume the raster is in that CRS
            # and reproject geometry if needed
            if geometry.crs != self._default_crs:
                geometry = geometry.to_crs(self._default_crs)
                print(f"CRS reprojection took {time.time() - reproject_start:.6f} seconds (using default CRS)")
        else:
            # No CRS anywhere - warn but proceed (risky)
            print("Warning: Neither raster nor geometry has a defined CRS. Spatial operations may be incorrect.")

        # Time coordinate extraction
        coord_start = time.time()
        # Extract x and y coordinates as numpy arrays
        x_coords = np.array([pt.x for pt in geometry])
        y_coords = np.array([pt.y for pt in geometry])
        
        # Time bounds checking
        bounds_start = time.time()
        # Vectorized bounds check using numpy
        bounds = self.data.bounds
        in_bounds = ((x_coords >= bounds.left) & (x_coords <= bounds.right) & 
                    (y_coords >= bounds.bottom) & (y_coords <= bounds.top))
        
        # Create result array filled with NaNs (for out-of-bounds points)
        result = np.full(len(geometry), np.nan)
        
        # Only process points that are within bounds
        if not np.any(in_bounds):
            print(f"Total method execution time: {time.time() - start_time:.6f} seconds (all points out of bounds)")
            return result  # All points are out of bounds
        
        # Time sampling and result processing
        sampling_start = time.time()
        # Get indices of in-bounds points
        in_bounds_indices = np.where(in_bounds)[0]
        in_bounds_count = len(in_bounds_indices)
        
        try:
            # Create coordinates array for in-bounds points directly with numpy
            stack_start = time.time()
            coords = np.column_stack((x_coords[in_bounds], y_coords[in_bounds]))
            
            # Sample the raster only for in-bounds coordinates
            raster_sample_start = time.time()
            samples = np.array(list(self.data.sample(coords, indexes=1))).flatten()
            
            # Vectorized handling of NoData values
            valid_samples = samples != self.data.nodata
            valid_count = np.sum(valid_samples)
            
            # Update result array at in-bounds positions with vectorized operation
            result[in_bounds_indices[valid_samples]] = samples[valid_samples].astype(float)
            print(f"Result processing took {time.time() - raster_sample_start:.6f} seconds, {valid_count}/{in_bounds_count} valid samples of {len(geometry)} points")
        
        except rasterio.RasterioIOError as e:
            print(f"Warning: Error during raster sampling: {e}")
        
        return result

    def close(self):
        """Closes the raster dataset."""
        self.data.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
