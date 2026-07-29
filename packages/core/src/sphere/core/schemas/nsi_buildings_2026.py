import os
from typing import Dict, Optional, Tuple
import duckdb
import geopandas as gpd
import pandas as pd
from sphere.core.schemas.buildings import Buildings


class NsiBuildings2026(Buildings):
    """NSI 2026 public buildings class loading from a geoparquet file.

    This class handles the newer NSI 2026 public data format distributed as a
    geoparquet file with a WKB ``shape`` geometry column.  Key differences from
    :class:`NsiBuildings` (which loads from a GeoPackage):

    - Loads from a **geoparquet** file (geopandas handles the WKB geometry
      column automatically via the ``geo`` metadata).
    - ``found_type`` is already a string code (``C``, ``S``, ``B``, ``P``,
      ``W``, ``I``, ``F``) — no numeric-to-string remapping is needed.
    - ``occtype`` is split at the first ``-`` character (e.g.
      ``"RES1-1SNB"`` → ``"RES1"``) in both the Python and DuckDB paths.
    - Overrides :meth:`to_duckdb` to load buildings **directly from the
      parquet file** using DuckDB's native ``read_parquet()`` — no
      Python-side GeoDataFrame round-trip for the main analysis.

    An optional *bbox* spatial filter ``(xmin, ymin, xmax, ymax)`` (WGS 84
    lon/lat) limits which buildings are loaded.  When analysing a local study
    area this dramatically reduces the working set from the nationwide 134 M
    row dataset.

    .. note::
        This class targets the **public** NSI 2026 release.  A future subclass
        will add support for the private/enhanced release, which carries
        additional fields while sharing the same base schema.
    """

    def __init__(
        self,
        parquet_file: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        overrides: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Args:
            parquet_file: Path to the NSI 2026 geoparquet file.
            bbox: Optional bounding-box filter ``(xmin, ymin, xmax, ymax)``
                in WGS 84 (EPSG:4326) coordinates.  When provided, only
                buildings whose ``x``/``y`` centroid falls within the box
                are loaded.  Derive from a raster's bounds to limit memory
                usage when working with the nationwide dataset.
            overrides: Optional field-name override dictionary passed to the
                parent :class:`Buildings` constructor.
        """
        drive, _ = os.path.splitdrive(parquet_file)
        if not drive:
            parquet_path = os.path.join(os.getcwd(), parquet_file)
        else:
            parquet_path = parquet_file

        self._parquet_path = parquet_path
        self._bbox = bbox

        # Build WHERE clause used in both the gdf load and to_duckdb override.
        self._where_clause = self._build_where_clause(bbox)

        # Load a lightweight GeoDataFrame using DuckDB for fast column-subset
        # reads.  This is needed for the raster-sampling step in
        # _create_hazard_table() which calls self.buildings.gdf.geometry.
        gdf = self._load_gdf()

        super().__init__(gdf, overrides)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_where_clause(
        bbox: Optional[Tuple[float, float, float, float]],
    ) -> str:
        if bbox is None:
            return ""
        xmin, ymin, xmax, ymax = bbox
        return (
            f"WHERE x BETWEEN {xmin} AND {xmax} "
            f"AND y BETWEEN {ymin} AND {ymax}"
        )

    def _load_gdf(self) -> gpd.GeoDataFrame:
        """Load a subset of columns from the parquet into a GeoDataFrame.

        Uses DuckDB for fast column-projection; only the columns needed for
        field-mapping and raster sampling are read.  ``occtype`` is split at
        the first ``-`` here so the parent class field-mapping and downstream
        DDF lookups receive the canonical occupancy code.
        """
        conn = duckdb.connect()
        try:
            df: pd.DataFrame = conn.execute(
                f"""
                SELECT
                    fd_id,
                    split_part(occtype, '-', 1)  AS occtype,
                    found_ht,
                    found_type,
                    num_story,
                    sqft,
                    val_struct,
                    val_cont,
                    bldgtype,
                    x,
                    y
                FROM read_parquet('{self._parquet_path}')
                {self._where_clause}
                """
            ).fetchdf()
        finally:
            conn.close()

        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["x"], df["y"]),
            crs="EPSG:4326",
        )
        return gdf

    # ------------------------------------------------------------------
    # DuckDB override — load directly from parquet, no GeoDataFrame detour
    # ------------------------------------------------------------------

    def to_duckdb(self, conn: duckdb.DuckDBPyConnection) -> None:  # type: ignore[override]
        """Load buildings from parquet into DuckDB using native SQL.

        Overrides :meth:`Buildings.to_duckdb` to bypass the GeoDataFrame
        round-trip.  DuckDB reads the parquet file directly, applying column
        renames, the ``occtype`` split, and the optional spatial filter in SQL.
        The resulting ``buildings`` table uses the canonical schema expected by
        :class:`~sphere.flood.analysis.hazus_flood.HazusFloodAnalysis` and
        :class:`~sphere.flood.analysis.hazus_flood2.HazusFloodAnalysis2`.

        Args:
            conn: An active DuckDB connection.
        """
        conn.execute("INSTALL spatial; LOAD spatial;")
        try:
            conn.execute("CALL register_geoarrow_extensions()")
        except Exception:
            pass

        conn.execute("DROP TABLE IF EXISTS buildings")
        conn.execute(
            f"""
            CREATE TABLE buildings AS
            SELECT
                fd_id                                  AS id,
                split_part(occtype, '-', 1)            AS occupancy_type,
                found_ht                               AS first_floor_height,
                found_type                             AS foundation_type,
                num_story                              AS number_stories,
                sqft                                   AS area,
                val_struct                             AS building_cost,
                val_cont                               AS content_cost,
                NULL::DOUBLE                           AS inventory_value,
                bldgtype                               AS general_building_type,
                NULL::VARCHAR                          AS bddf_id,
                NULL::VARCHAR                          AS cddf_id,
                NULL::VARCHAR                          AS iddf_id,
                shape                                  AS geometry
            FROM read_parquet('{self._parquet_path}')
            {self._where_clause}
            """
        )
