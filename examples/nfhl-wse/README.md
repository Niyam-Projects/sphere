# NFHL WSE-Based Flood Loss Analysis — Harris County, TX

This example shows how to run a Hazus-methodology flood loss analysis using a
**Water Surface Elevation (WSE) raster** instead of a pre-computed depth raster.
It demonstrates the modular override pattern in `sphere` — only the hazard step
changes; all vulnerability, loss, debris, and restoration logic is reused as-is.

## Background

Standard flood analysis workflows provide a *depth* raster where each pixel already
represents the depth of water above the ground surface. NFHL (National Flood Hazard
Layer) products and many hydraulic models publish results as **Water Surface
Elevation (WSE)** rasters instead — the pixel value is the absolute water-surface
elevation (e.g., feet NAVD88), not a relative depth.

To use a WSE raster with Hazus methodology you need to subtract the ground
elevation at each structure:

```
depth             = WSE_raster_value − ground_elv   # depth above ground
depth_in_structure = depth − found_ht               # depth inside the building
```

`ground_elv` (ground elevation, ft NAVD88) and `found_ht` (first floor height above
ground, ft) are both standard fields in the National Structure Inventory (NSI).

## Files

| File | Description |
|---|---|
| `nfhl_wse_analysis.py` | Main analysis script |

## Inputs

| Input | Path |
|---|---|
| NSI Texas GPKG | `E:/projects/asfpm2026/nsi_2022_48.gpkg` |
| WSE raster (COG) | `E:/projects/asfpm2026/harris_county_wse_cog.tif` |

The Texas state NSI file is subsetted to **Harris County** (FIPS `48201`) using
the `county` column before any analysis runs, avoiding unnecessary processing of
the full state dataset (~1.5 M structures).

## How the Override Works

`sphere` uses a template-method pattern in `HazusFloodAnalysis`. The protected
method `_compute_flood_depth(gdf)` is responsible for returning flood depth values
for each building. By default it samples the `depth_grid` raster directly.

`WseHazusFloodAnalysis` overrides just this one method:

```python
class WseHazusFloodAnalysis(HazusFloodAnalysis):
    def _compute_flood_depth(self, gdf):
        wse_values = pd.Series(
            self.depth_grid.get_value_vectorized(gdf.geometry),
            index=gdf.index,
        )
        return wse_values - gdf["ground_elv"]   # WSE − ground elevation = depth
```

Everything after `_compute_flood_depth` — including the `depth_in_structure`
calculation, vulnerability lookup, loss estimates, debris, and restoration — runs
exactly as it does in the standard analysis.

## Running

```bash
cd examples/nfhl-wse
python nfhl_wse_analysis.py
```

Results are saved to `E:/projects/asfpm2026/sphere_harris_wse_results.parquet`.

## Extending Further

The same override pattern can be applied to other hazard sources:

- **Multiple return-period WSE rasters** — loop over rasters and call
  `calculate_losses()` for each.
- **Coastal surge + riverine combined** — blend two WSE grids before subtracting
  ground elevation.
- **Custom ground elevation source** — override `grnd_elv` with a higher-resolution
  DEM by adding the column to the GeoDataFrame before analysis.
