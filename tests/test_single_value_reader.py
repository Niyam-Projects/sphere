import numpy as np
import geopandas as gpd
import pandas as pd

import types
import pytest

from sphere.flood.single_value_reader import SingleValueRaster


class DummyDataset:
    def __init__(self, bounds, nodata=None, crs=None):
        self.bounds = types.SimpleNamespace(left=bounds[0], bottom=bounds[1], right=bounds[2], top=bounds[3])
        self.nodata = nodata
        self.crs = crs

    def sample(self, coords, indexes=1):
        # return a generator that yields one value per coord
        for x, y in coords:
            # simple function: value = x + y
            yield (x + y,)

    def close(self):
        pass


def test_get_value_vectorized_out_of_bounds(monkeypatch):
    # Build a small GeoSeries with points both in and out of bounds
    df = pd.DataFrame({"Longitude": [0.0, 100.0], "Latitude": [0.0, 100.0]})
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326")

    # Monkeypatch rasterio.open to return a dummy dataset
    dummy = DummyDataset(bounds=(-10.0, -10.0, 10.0, 10.0), nodata=None, crs="EPSG:4326")

    # Ensure isinstance(self.data, rasterio.DatasetReader) check passes by
    # monkeypatching the DatasetReader type in the module to our DummyDataset.
    monkeypatch.setattr('sphere.flood.single_value_reader.rasterio.DatasetReader', DummyDataset, raising=False)
    monkeypatch.setattr('rasterio.open', lambda _path: dummy)

    svr = SingleValueRaster("/some/fake/path.tif")

    # Call vectorized reader; second point is out of bounds and should yield NaN
    result = svr.get_value_vectorized(gdf.geometry)
    assert isinstance(result, np.ndarray)
    assert np.isfinite(result[0])
    assert np.isnan(result[1])
