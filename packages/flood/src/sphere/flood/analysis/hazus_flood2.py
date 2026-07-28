"""HazusFloodAnalysis2 — DuckDB-only flood loss calculator with the updated
damage-function methodology.

Key differences from ``HazusFloodAnalysis``:

* Uses the new lookup tables (``df_lookup_structures/contents/inventory.csv``)
  and damage curves (``damage_curves_structure/contents/inventory.csv``) copied
  from the inland-consequences project.
* Riverine peril type is determined by velocity **and** duration:
  ``R`` + ``H/L`` (velocity) + ``L/S`` (duration) → e.g. ``RLS``, ``RHL``.
  Requires ``velocity_grid`` and ``duration_grid`` rasters.  Falls back to
  ``RLS`` if grids are absent.
* Coastal peril type uses the updated codes based on depth:
  ``CST`` (< 3 ft), ``CMV`` (3–6 ft), ``CHW`` (≥ 6 ft).
* Foundation type is normalised to the 4-letter codes expected by the new lookup
  tables: ``BASEMENT``, ``PILE``, ``SHALLOW``, ``SLAB``.
* Damage function matching uses a CROSS JOIN approach with direct attribute
  equality (construction type, occupancy, stories, area, foundation, peril),
  with frequency-weighted averaging when multiple curves match.
* No Python/GeoDataFrame ``calculate_losses()`` path — DuckDB only.
"""

import re
import numpy as np
import pandas as pd
from typing import TYPE_CHECKING, Optional

from sphere.core.schemas.buildings import Buildings
from sphere.core.schemas.abstract_raster_reader import RasterReader

try:
    import importlib.resources as resources
except ImportError:
    import importlib_resources as resources  # type: ignore[no-redef]

if TYPE_CHECKING:
    import duckdb


class HazusFloodAnalysis2:
    """DuckDB-based flood loss calculator using the updated (inland-consequences)
    damage function methodology.

    Peril type assignment:
    - **Riverine** (``flood_type="R"``):
      ``R`` + velocity class (``H`` ≥ 5 ft/s, ``L`` otherwise) +
      duration class (``L`` ≥ 72 h, ``S`` otherwise).
      Examples: ``RLS``, ``RHL``, ``RLL``, ``RHS``.
      Requires ``velocity_grid`` + ``duration_grid``; falls back to ``RLS`` if absent.
    - **Coastal** (``flood_type="C"``):
      depth ≥ 6 ft → ``CHW`` (Coastal High Wave),
      depth ≥ 3 ft → ``CMV`` (Coastal Moderate Wave),
      depth < 3 ft → ``CST`` (Coastal Stillwater).

    Usage::

        import duckdb
        conn = duckdb.connect(":memory:")
        analyzer = HazusFloodAnalysis2(
            buildings=my_buildings,
            depth_grid=depth_raster,
            flood_type="R",
            velocity_grid=vel_raster,
            duration_grid=dur_raster,
        )
        losses_df = analyzer.calculate_losses_duckdb(conn)
    """

    def __init__(
        self,
        buildings: Buildings,
        depth_grid: RasterReader,
        flood_type: str = "R",
        velocity_grid: Optional[RasterReader] = None,
        duration_grid: Optional[RasterReader] = None,
    ):
        """
        Args:
            buildings: Buildings object.
            depth_grid: Raster reader for flood depth values (ft).
            flood_type: ``"R"`` for riverine or ``"C"`` for coastal.
            velocity_grid: Optional raster reader for flood velocity (ft/s).
                Used together with ``duration_grid`` for riverine peril classification.
            duration_grid: Optional raster reader for flood duration (hours).
        """
        self.buildings = buildings
        self.depth_grid = depth_grid
        self.flood_type = flood_type.upper()
        self.velocity_grid = velocity_grid
        self.duration_grid = duration_grid

    # -------------------------------------------------------------------------
    # Static infrastructure helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _setup_spatial_extensions(conn: "duckdb.DuckDBPyConnection") -> None:
        conn.execute("INSTALL spatial; LOAD spatial;")
        try:
            conn.execute("CALL register_geoarrow_extensions()")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Hazard table
    # -------------------------------------------------------------------------

    def _create_hazard_table(self, conn: "duckdb.DuckDBPyConnection") -> None:
        """Sample depth (and optionally velocity/duration) at each building point.

        Only rows with depth > 0 are stored (non-flooded buildings are excluded).

        Columns: ``id``, ``depth``, and optionally ``velocity``, ``duration``.
        """
        import pyarrow as pa

        gdf = self.buildings.gdf
        geometries = gdf.geometry
        depths = np.asarray(self.depth_grid.get_value_vectorized(geometries))

        id_col = self.buildings.fields.get_field_name("id")
        ids = gdf[id_col].values if id_col in gdf.columns else gdf.index.values

        data: dict = {"id": ids, "depth": depths}
        if self.velocity_grid is not None:
            data["velocity"] = np.asarray(
                self.velocity_grid.get_value_vectorized(geometries)
            )
        if self.duration_grid is not None:
            data["duration"] = np.asarray(
                self.duration_grid.get_value_vectorized(geometries)
            )

        hazard_df = pd.DataFrame(data)
        hazard_df = hazard_df[hazard_df["depth"] > 0].reset_index(drop=True)

        arrow_table = pa.Table.from_pandas(hazard_df)
        conn.register("_hazard_arrow_reg", arrow_table)
        conn.execute("DROP TABLE IF EXISTS hazard")
        conn.execute("CREATE TABLE hazard AS SELECT * FROM _hazard_arrow_reg")
        try:
            conn.unregister("_hazard_arrow_reg")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Vulnerability (lookup) tables
    # -------------------------------------------------------------------------

    def _create_vulnerability_tables(self, conn: "duckdb.DuckDBPyConnection") -> None:
        """Load the updated lookup tables and damage curves into DuckDB.

        Creates tables:
            ``xref_structures``        — df_lookup_structures.csv
            ``xref_contents``          — df_lookup_contents.csv
            ``xref_inventory``         — df_lookup_inventory.csv
            ``damage_curves_structure`` — damage_curves_structure.csv
            ``damage_curves_contents``  — damage_curves_contents.csv
            ``damage_curves_inventory`` — damage_curves_inventory.csv
        """
        for table_name, filename in [
            ("xref_structures",         "df_lookup_structures.csv"),
            ("xref_contents",           "df_lookup_contents.csv"),
            ("xref_inventory",          "df_lookup_inventory.csv"),
            ("damage_curves_structure", "damage_curves_structure.csv"),
            ("damage_curves_contents",  "damage_curves_contents.csv"),
            ("damage_curves_inventory", "damage_curves_inventory.csv"),
        ]:
            with (
                resources.files("sphere.data")
                .joinpath(filename)
                .open("r", encoding="utf-8-sig") as f
            ):
                df = pd.read_csv(f)

            import pyarrow as pa
            arrow_table = pa.Table.from_pandas(df)
            conn.register(f"_reg_{table_name}", arrow_table)
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM _reg_{table_name}")
            try:
                conn.unregister(f"_reg_{table_name}")
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Foundation type normalisation
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_foundation_types(conn: "duckdb.DuckDBPyConnection") -> None:
        """Convert building foundation type codes to the 4-word codes used by the
        new lookup tables: ``BASEMENT``, ``PILE``, ``SHALLOW``, ``SLAB``.

        Mapping:
            ``B``, ``4``, ``2``          → ``BASEMENT``
            ``W``, ``P``, ``I``, ``C``,
            ``M``, ``3``                 → ``PILE``
            ``F``, ``S``, ``1``          → ``SHALLOW``
            Already-full-word codes are left unchanged.
        """
        conn.execute("""
            UPDATE buildings
            SET foundation_type = CASE
                WHEN UPPER(CAST(foundation_type AS VARCHAR)) IN ('BASEMENT') THEN 'BASEMENT'
                WHEN UPPER(CAST(foundation_type AS VARCHAR)) IN ('PILE')     THEN 'PILE'
                WHEN UPPER(CAST(foundation_type AS VARCHAR)) IN ('SHALLOW')  THEN 'SHALLOW'
                WHEN UPPER(CAST(foundation_type AS VARCHAR)) IN ('SLAB')     THEN 'SLAB'
                WHEN CAST(foundation_type AS VARCHAR) IN ('B', '4', '2')     THEN 'BASEMENT'
                WHEN CAST(foundation_type AS VARCHAR) IN ('W', 'P', 'I', 'C', 'M', '3') THEN 'PILE'
                WHEN CAST(foundation_type AS VARCHAR) IN ('F', 'S', '1')     THEN 'SHALLOW'
                ELSE NULL
            END
        """)

    # -------------------------------------------------------------------------
    # Peril type assignment
    # -------------------------------------------------------------------------

    def _assign_flood_peril_type_sql(self, conn: "duckdb.DuckDBPyConnection") -> None:
        """Assign ``flood_peril_type`` on the buildings table.

        - **Riverine** (``flood_type="R"``): uses velocity + duration to produce
          ``RLS``, ``RHL``, ``RLL``, or ``RHS``.  Falls back to ``RLS`` when
          ``velocity_grid``/``duration_grid`` are not provided.
        - **Coastal** (``flood_type="C"``): uses depth thresholds to produce
          ``CST``, ``CMV``, or ``CHW``.

        Args:
            conn: Active DuckDB connection.  Expects ``buildings`` and ``hazard``.
        """
        conn.execute("ALTER TABLE buildings ADD COLUMN IF NOT EXISTS flood_peril_type VARCHAR")
        if self.flood_type == "C":
            self._assign_peril_coastal_depth_sql(conn)
        else:
            if self.velocity_grid is not None and self.duration_grid is not None:
                self._assign_peril_riverine_velocity_duration_sql(conn)
            else:
                self._assign_peril_riverine_default_sql(conn)

    @staticmethod
    def _assign_peril_riverine_default_sql(conn: "duckdb.DuckDBPyConnection") -> None:
        """Assign ``RLS`` (Riverine Low Short) to all buildings when no
        velocity/duration rasters are available.

        Args:
            conn: Active DuckDB connection.
        """
        conn.execute("UPDATE buildings SET flood_peril_type = 'RLS' WHERE flood_peril_type IS NULL")

    @staticmethod
    def _assign_peril_riverine_velocity_duration_sql(conn: "duckdb.DuckDBPyConnection") -> None:
        """Assign riverine peril type using sampled velocity and duration values.

        Thresholds:
            velocity ≥ 5 ft/s  → ``H`` (High); otherwise → ``L`` (Low)
            duration ≥ 72 h    → ``L`` (Long); otherwise → ``S`` (Short)

        The maximum velocity/duration across all hazard rows is used per building.
        NULL values are treated as 0.

        Args:
            conn: Active DuckDB connection.  Expects ``hazard`` table with
                  ``velocity`` and ``duration`` columns.
        """
        conn.execute("""
            UPDATE buildings
            SET flood_peril_type = (
                SELECT
                    'R'
                    || CASE WHEN MAX(COALESCE(h.velocity, 0)) >= 5 THEN 'H' ELSE 'L' END
                    || CASE WHEN MAX(COALESCE(h.duration, 0)) >= 72 THEN 'L' ELSE 'S' END
                FROM hazard h
                WHERE h.id = buildings.id
                GROUP BY h.id
            )
            WHERE buildings.flood_peril_type IS NULL
        """)
        conn.execute("UPDATE buildings SET flood_peril_type = 'RLS' WHERE flood_peril_type IS NULL")

    @staticmethod
    def _assign_peril_coastal_depth_sql(conn: "duckdb.DuckDBPyConnection") -> None:
        """Assign coastal peril type based on flood depth.

        Thresholds:
            depth ≥ 6 ft  → ``CHW`` (Coastal High Wave)
            depth ≥ 3 ft  → ``CMV`` (Coastal Moderate Wave)
            depth < 3 ft  → ``CST`` (Coastal Stillwater)

        Args:
            conn: Active DuckDB connection.  Expects ``buildings`` and ``hazard``.
        """
        conn.execute("""
            UPDATE buildings
            SET flood_peril_type = (
                SELECT CASE
                           WHEN h.depth >= 6 THEN 'CHW'
                           WHEN h.depth >= 3 THEN 'CMV'
                           ELSE 'CST'
                       END
                FROM hazard h
                WHERE h.id = buildings.id
                LIMIT 1
            )
            WHERE buildings.flood_peril_type IS NULL
        """)
        conn.execute("UPDATE buildings SET flood_peril_type = 'CST' WHERE flood_peril_type IS NULL")

    # -------------------------------------------------------------------------
    # Damage function matching
    # -------------------------------------------------------------------------

    def _gather_damage_functions(self, conn: "duckdb.DuckDBPyConnection") -> None:
        """Match buildings to damage functions via cross-join attribute matching.

        For each of structure, content, and inventory, cross-joins the buildings
        table with the corresponding xref table, keeps rows where all non-NULL
        attributes match, then computes probability weights as the relative
        frequency of each curve across the matched set.

        Matching attributes:
          - Structure: occupancy_type, foundation_type, number_stories, area
            (sqft range), general_building_type (construction), flood_peril_type
          - Contents: occupancy_type, foundation_type, number_stories,
            general_building_type, flood_peril_type, area (sqft range)
          - Inventory: occupancy_type, foundation_type, flood_peril_type

        Creates tables:
            ``structure_damage_functions`` (id, ddf_id, weight)
            ``content_damage_functions``   (id, ddf_id, weight)
            ``inventory_damage_functions`` (id, ddf_id, weight)
        """
        # Structure
        conn.execute("DROP TABLE IF EXISTS structure_damage_functions")
        conn.execute("""
            CREATE TABLE structure_damage_functions AS
            WITH curve_matches AS (
                SELECT
                    b.id,
                    c.damage_function_id,
                    CASE
                        WHEN b.occupancy_type IS NOT NULL AND c.occupancy_type IS NOT NULL
                            AND b.occupancy_type != c.occupancy_type THEN 0
                        WHEN b.foundation_type IS NOT NULL AND c.foundation_type IS NOT NULL
                            AND b.foundation_type != c.foundation_type THEN 0
                        WHEN b.number_stories IS NOT NULL AND c.story_min IS NOT NULL AND c.story_max IS NOT NULL
                            AND NOT (b.number_stories BETWEEN c.story_min AND c.story_max) THEN 0
                        WHEN b.area IS NOT NULL
                            AND NOT (
                                (c.sqft_min IS NULL OR b.area >= c.sqft_min)
                                AND (c.sqft_max IS NULL OR b.area <= c.sqft_max)
                            ) THEN 0
                        WHEN b.general_building_type IS NOT NULL AND c.construction_type IS NOT NULL
                            AND b.general_building_type != c.construction_type THEN 0
                        WHEN b.flood_peril_type IS NOT NULL AND c.flood_peril_type IS NOT NULL
                            AND b.flood_peril_type != c.flood_peril_type THEN 0
                        ELSE 1
                    END AS is_match
                FROM buildings b
                CROSS JOIN xref_structures c
            ),
            filtered AS (
                SELECT id, damage_function_id
                FROM curve_matches WHERE is_match = 1
            ),
            frequencies AS (
                SELECT
                    id, damage_function_id,
                    COUNT(*) OVER (PARTITION BY id) AS total_matches,
                    COUNT(*) OVER (PARTITION BY id, damage_function_id) AS curve_count
                FROM filtered
            )
            SELECT DISTINCT
                id,
                damage_function_id AS ddf_id,
                CAST(curve_count AS DOUBLE) / NULLIF(total_matches, 0) AS weight
            FROM frequencies
        """)

        # Content
        conn.execute("DROP TABLE IF EXISTS content_damage_functions")
        conn.execute("""
            CREATE TABLE content_damage_functions AS
            WITH curve_matches AS (
                SELECT
                    b.id,
                    c.damage_function_id,
                    CASE
                        WHEN b.occupancy_type IS NOT NULL AND c.occupancy_type IS NOT NULL
                            AND b.occupancy_type != c.occupancy_type THEN 0
                        WHEN b.foundation_type IS NOT NULL AND c.foundation_type IS NOT NULL
                            AND b.foundation_type != c.foundation_type THEN 0
                        WHEN b.number_stories IS NOT NULL AND c.story_min IS NOT NULL AND c.story_max IS NOT NULL
                            AND NOT (b.number_stories BETWEEN c.story_min AND c.story_max) THEN 0
                        WHEN b.general_building_type IS NOT NULL AND c.construction_type IS NOT NULL
                            AND b.general_building_type != c.construction_type THEN 0
                        WHEN b.flood_peril_type IS NOT NULL AND c.flood_peril_type IS NOT NULL
                            AND b.flood_peril_type != c.flood_peril_type THEN 0
                        WHEN b.area IS NOT NULL AND c.sqft_min IS NOT NULL AND b.area < c.sqft_min THEN 0
                        WHEN b.area IS NOT NULL AND c.sqft_max IS NOT NULL AND b.area > c.sqft_max THEN 0
                        ELSE 1
                    END AS is_match
                FROM buildings b
                CROSS JOIN xref_contents c
            ),
            filtered AS (
                SELECT id, damage_function_id
                FROM curve_matches WHERE is_match = 1
            ),
            frequencies AS (
                SELECT
                    id, damage_function_id,
                    COUNT(*) OVER (PARTITION BY id) AS total_matches,
                    COUNT(*) OVER (PARTITION BY id, damage_function_id) AS curve_count
                FROM filtered
            )
            SELECT DISTINCT
                id,
                damage_function_id AS ddf_id,
                CAST(curve_count AS DOUBLE) / NULLIF(total_matches, 0) AS weight
            FROM frequencies
        """)

        # Inventory
        conn.execute("DROP TABLE IF EXISTS inventory_damage_functions")
        conn.execute("""
            CREATE TABLE inventory_damage_functions AS
            WITH curve_matches AS (
                SELECT
                    b.id,
                    c.damage_function_id,
                    CASE
                        WHEN b.occupancy_type IS NOT NULL AND c.occupancy_type IS NOT NULL
                            AND b.occupancy_type != c.occupancy_type THEN 0
                        WHEN b.foundation_type IS NOT NULL AND c.foundation_type IS NOT NULL
                            AND b.foundation_type != c.foundation_type THEN 0
                        WHEN b.flood_peril_type IS NOT NULL AND c.flood_peril_type IS NOT NULL
                            AND b.flood_peril_type != c.flood_peril_type THEN 0
                        ELSE 1
                    END AS is_match
                FROM buildings b
                CROSS JOIN xref_inventory c
            ),
            filtered AS (
                SELECT id, damage_function_id
                FROM curve_matches WHERE is_match = 1
            ),
            frequencies AS (
                SELECT
                    id, damage_function_id,
                    COUNT(*) OVER (PARTITION BY id) AS total_matches,
                    COUNT(*) OVER (PARTITION BY id, damage_function_id) AS curve_count
                FROM filtered
            )
            SELECT DISTINCT
                id,
                damage_function_id AS ddf_id,
                CAST(curve_count AS DOUBLE) / NULLIF(total_matches, 0) AS weight
            FROM frequencies
        """)

    def _gather_missing_functions(self, conn: "duckdb.DuckDBPyConnection") -> None:
        """Fallback for buildings unmatched by ``_gather_damage_functions``.

        Clamps out-of-range number_stories/area to the nearest bound and re-runs
        the matching on non-range attributes only, then inserts results into
        ``structure_damage_functions``.

        Content and inventory lookups use simple equality so unmatched buildings
        get no fallback (NULL damage → 0 loss).

        Args:
            conn: Active DuckDB connection.
        """
        conn.execute("""
            INSERT INTO structure_damage_functions (id, ddf_id, weight)
            WITH missing AS (
                SELECT b.*
                FROM buildings b
                LEFT JOIN structure_damage_functions sdf ON b.id = sdf.id
                WHERE sdf.id IS NULL
                  AND b.id IN (SELECT id FROM hazard)
            ),
            -- Non-range attribute match only (skip story/sqft range filters)
            candidates AS (
                SELECT
                    b.id,
                    c.damage_function_id,
                    c.story_min, c.story_max,
                    c.sqft_min,  c.sqft_max
                FROM missing b
                CROSS JOIN xref_structures c
                WHERE (
                    CASE
                        WHEN b.occupancy_type IS NOT NULL AND c.occupancy_type IS NOT NULL
                            AND b.occupancy_type != c.occupancy_type THEN 0
                        WHEN b.general_building_type IS NOT NULL AND c.construction_type IS NOT NULL
                            AND b.general_building_type != c.construction_type THEN 0
                        WHEN b.flood_peril_type IS NOT NULL AND c.flood_peril_type IS NOT NULL
                            AND b.flood_peril_type != c.flood_peril_type THEN 0
                        ELSE 1
                    END = 1
                )
            ),
            -- Per-building range bounds
            bounds AS (
                SELECT
                    id, damage_function_id,
                    MIN(story_min) OVER (PARTITION BY id) AS g_story_min,
                    MAX(story_max) OVER (PARTITION BY id) AS g_story_max,
                    MIN(sqft_min)  OVER (PARTITION BY id) AS g_sqft_min,
                    MAX(sqft_max)  OVER (PARTITION BY id) AS g_sqft_max
                FROM candidates
            ),
            clamped AS (
                SELECT DISTINCT
                    c.id,
                    c.damage_function_id,
                    COALESCE(LEAST(GREATEST(m.number_stories, b.g_story_min), b.g_story_max), b.g_story_min) AS eff_stories,
                    COALESCE(LEAST(GREATEST(m.area, b.g_sqft_min), b.g_sqft_max), b.g_sqft_min) AS eff_sqft
                FROM candidates c
                JOIN missing m ON c.id = m.id
                JOIN bounds  b ON c.id = b.id AND c.damage_function_id = b.damage_function_id
            ),
            range_matched AS (
                SELECT cl.id, cl.damage_function_id
                FROM clamped cl
                JOIN xref_structures xs ON cl.damage_function_id = xs.damage_function_id
                WHERE (xs.story_min IS NULL OR cl.eff_stories >= xs.story_min)
                  AND (xs.story_max IS NULL OR cl.eff_stories <= xs.story_max)
                  AND (xs.sqft_min  IS NULL OR cl.eff_sqft   >= xs.sqft_min)
                  AND (xs.sqft_max  IS NULL OR cl.eff_sqft   <= xs.sqft_max)
            ),
            frequencies AS (
                SELECT
                    id, damage_function_id,
                    COUNT(*) OVER (PARTITION BY id) AS total_matches,
                    COUNT(*) OVER (PARTITION BY id, damage_function_id) AS curve_count
                FROM range_matched
            )
            SELECT DISTINCT
                id,
                damage_function_id AS ddf_id,
                CAST(curve_count AS DOUBLE) / NULLIF(total_matches, 0) AS weight
            FROM frequencies
        """)

    # -------------------------------------------------------------------------
    # Damage statistics (interpolation)
    # -------------------------------------------------------------------------

    def _compute_damage_function_statistics(self, conn: "duckdb.DuckDBPyConnection") -> None:
        """Interpolate damage percentages from the new damage curves tables.

        Unpivots the wide ft-columns, builds interpolation segments, evaluates
        each building's adjusted depth (depth − first_floor_height), and
        computes a probability-weighted damage percent.

        Creates tables:
            ``damage_function_statistics``           (id, damage_percent_mean)
            ``content_damage_function_statistics``   (id, damage_percent_mean)
            ``inventory_damage_function_statistics`` (id, damage_percent_mean)
        """
        for stat_table, fn_table, ddf_table in [
            ("damage_function_statistics",           "structure_damage_functions", "damage_curves_structure"),
            ("content_damage_function_statistics",   "content_damage_functions",   "damage_curves_contents"),
            ("inventory_damage_function_statistics", "inventory_damage_functions", "damage_curves_inventory"),
        ]:
            cols = conn.execute(f"DESCRIBE {ddf_table}").df()["column_name"].tolist()
            ft_cols = [c for c in cols if re.match(r"^ft\d+(m)?$", c) or re.match(r"^ft\d+_\d+(m)?$", c)]

            unpivot_pairs = []
            for col in ft_cols:
                m = re.match(r"^ft(\d+)_(\d+)(m)?$", col)
                if m:
                    whole, frac = int(m.group(1)), int(m.group(2))
                    depth_val = -(whole + frac / 10.0) if m.group(3) == "m" else (whole + frac / 10.0)
                    unpivot_pairs.append((col, depth_val))
                    continue
                m = re.match(r"^ft(\d+)(m)?$", col)
                if m:
                    depth_val = -int(m.group(1)) if m.group(2) == "m" else int(m.group(1))
                    unpivot_pairs.append((col, depth_val))

            if not unpivot_pairs:
                conn.execute(f"DROP TABLE IF EXISTS {stat_table}")
                conn.execute(
                    f"CREATE TABLE {stat_table} AS "
                    f"SELECT id, 0.0::DOUBLE AS damage_percent_mean FROM buildings WHERE FALSE"
                )
                continue

            unpivot_cols = ", ".join(f"'{col}'" for col, _ in unpivot_pairs)
            depth_case = "CASE col_name " + " ".join(
                f"WHEN '{col}' THEN {depth_val:.4f}" for col, depth_val in unpivot_pairs
            ) + " END"

            conn.execute(f"DROP TABLE IF EXISTS {stat_table}")
            conn.execute(f"""
                CREATE TABLE {stat_table} AS
                WITH
                ddf_long AS (
                    SELECT
                        DDF_ID AS ddf_id,
                        {depth_case} AS depth_ft,
                        col_value::DOUBLE AS damage_pct
                    FROM (
                        UNPIVOT {ddf_table}
                        ON {unpivot_cols}
                        INTO NAME col_name VALUE col_value
                    )
                ),
                ddf_segments AS (
                    SELECT
                        ddf_id,
                        depth_ft AS depth_lower,
                        LEAD(depth_ft)  OVER (PARTITION BY ddf_id ORDER BY depth_ft) AS depth_upper,
                        damage_pct AS pct_lower,
                        LEAD(damage_pct) OVER (PARTITION BY ddf_id ORDER BY depth_ft) AS pct_upper
                    FROM ddf_long
                ),
                eval AS (
                    SELECT
                        b.id,
                        fn.ddf_id,
                        fn.weight,
                        (h.depth - COALESCE(b.first_floor_height, 0)) AS eval_depth
                    FROM buildings b
                    JOIN {fn_table} fn ON b.id = fn.id
                    JOIN hazard h      ON b.id = h.id
                ),
                clamped AS (
                    SELECT
                        e.id, e.ddf_id, e.weight,
                        GREATEST(
                            (SELECT MIN(depth_ft) FROM ddf_long dl WHERE dl.ddf_id = e.ddf_id),
                            LEAST(
                                (SELECT MAX(depth_ft) FROM ddf_long dl WHERE dl.ddf_id = e.ddf_id),
                                e.eval_depth
                            )
                        ) AS clamped_depth
                    FROM eval e
                ),
                matched AS (
                    SELECT
                        c.id,
                        c.weight,
                        s.pct_lower + (
                            CASE
                                WHEN s.depth_upper IS NULL OR s.depth_upper = s.depth_lower THEN 0
                                ELSE (c.clamped_depth - s.depth_lower)
                                     / (s.depth_upper - s.depth_lower)
                                     * (s.pct_upper - s.pct_lower)
                            END
                        ) AS interp_pct
                    FROM clamped c
                    JOIN ddf_segments s
                      ON c.ddf_id = s.ddf_id
                     AND c.clamped_depth >= s.depth_lower
                     AND (s.depth_upper IS NULL OR c.clamped_depth < s.depth_upper)
                    QUALIFY ROW_NUMBER() OVER (
                        PARTITION BY c.id, c.ddf_id ORDER BY s.depth_lower DESC
                    ) = 1
                )
                SELECT
                    id,
                    SUM(weight * LEAST(interp_pct, 100.0)) AS damage_percent_mean
                FROM matched
                GROUP BY id
            """)

    # -------------------------------------------------------------------------
    # Loss calculation
    # -------------------------------------------------------------------------

    @staticmethod
    def _calculate_losses_sql(conn: "duckdb.DuckDBPyConnection") -> None:
        """Compute monetary losses per building into a ``losses`` table."""
        conn.execute("DROP TABLE IF EXISTS losses")
        conn.execute("""
            CREATE TABLE losses AS
            SELECT
                b.id,
                COALESCE(b.building_cost, 0)
                    * COALESCE(ds.damage_percent_mean, 0) / 100.0  AS building_loss,
                COALESCE(b.content_cost, 0)
                    * COALESCE(cs.damage_percent_mean, 0) / 100.0  AS content_loss,
                COALESCE(b.inventory_value, 0)
                    * COALESCE(ivs.damage_percent_mean, 0) / 100.0 AS inventory_loss
            FROM buildings b
            LEFT JOIN damage_function_statistics           ds  ON b.id = ds.id
            LEFT JOIN content_damage_function_statistics   cs  ON b.id = cs.id
            LEFT JOIN inventory_damage_function_statistics ivs ON b.id = ivs.id
            WHERE b.id IN (SELECT id FROM hazard)
        """)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def calculate_losses_duckdb(self, conn: "duckdb.DuckDBPyConnection") -> pd.DataFrame:
        """Calculate flood losses using the updated DuckDB pipeline.

        Pipeline steps:
            1. Install spatial extensions
            2. Load buildings into ``buildings`` table (standardized schema)
            3. Sample hazard raster(s) into ``hazard`` table
            4. Load updated vulnerability lookup tables and damage curves
            5. Normalise foundation type codes to BASEMENT/PILE/SHALLOW/SLAB
            6. Assign flood peril type (riverine vel/dur or coastal depth)
            7. Match damage functions via cross-join attribute matching
            8. Fill missing function fallbacks (range clamping)
            9. Compute interpolated damage statistics
            10. Calculate monetary losses

        Args:
            conn: An active DuckDB connection.

        Returns:
            pd.DataFrame: Rows for flooded buildings with columns
                ``id``, ``building_loss``, ``content_loss``, ``inventory_loss``.
        """
        self._setup_spatial_extensions(conn)
        self.buildings.to_duckdb(conn)
        self._create_hazard_table(conn)
        self._create_vulnerability_tables(conn)
        self._normalize_foundation_types(conn)
        self._assign_flood_peril_type_sql(conn)
        self._gather_damage_functions(conn)
        self._gather_missing_functions(conn)
        self._compute_damage_function_statistics(conn)
        self._calculate_losses_sql(conn)
        return conn.execute("SELECT * FROM losses").df()
