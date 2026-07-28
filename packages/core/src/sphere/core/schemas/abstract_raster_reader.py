from typing import Protocol
import numpy as np
import geopandas as gpd


class RasterReader(Protocol):
    """Protocol for reading flood depth values from raster data.

    Any class implementing `get_value` and `get_value_vectorized` with
    matching signatures satisfies this protocol, regardless of inheritance.
    """

    def get_value(self, lon: float, lat: float) -> float:
        """Returns flood depth at a given point."""
        ...

    def get_value_vectorized(self, geometry: gpd.GeoSeries) -> np.ndarray:
        """Returns flood depth for multiple locations in a vectorized way."""
        ...