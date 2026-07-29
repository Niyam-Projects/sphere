import marimo

__generated_with = "0.20.3"
app = marimo.App(width="medium", app_title="SPHERE Flood Analysis")


@app.cell
def _():
    """Setup: Import all required libraries"""
    import marimo as mo
    import os
    import time
    import duckdb
    import pandas as pd
    from pathlib import Path

    # SPHERE modules
    from sphere.core.schemas.nsi_buildings_2026 import NsiBuildings2026
    from sphere.flood.analysis.hazus_flood import HazusFloodAnalysis
    from sphere.flood.analysis.hazus_flood2 import HazusFloodAnalysis2
    from sphere.flood.default_vulnerability import DefaultFloodVulnerability
    from sphere.flood.single_value_reader import SingleValueRaster

    return (
        HazusFloodAnalysis,
        HazusFloodAnalysis2,
        DefaultFloodVulnerability,
        NsiBuildings2026,
        Path,
        SingleValueRaster,
        duckdb,
        mo,
        os,
        pd,
        time,
    )


@app.cell
def _(mo):
    mo.md("""
    # 🌊 SPHERE Flood Analysis

    Interactive flood loss analysis using the SPHERE library (Python implementation of HAZUS flood methodology).

    /// admonition | Tip
        type: info

    Default paths are pre-filled based on the repository's `examples/` folder.  Edit them to point to your data files.
    ///

    [Documentation](https://github.com/Niyam-Projects/sphere) | [HAZUS Methodology](https://www.fema.gov/flood-maps/products-tools/hazus)
    """)
    return


@app.cell
def _(mo):
    workflow_diagram = '''
    graph LR
        A[Load Buildings] --> B[Load Hazard Raster]
        B --> C[Sample Depths at Buildings]
        C --> D[Match Damage Functions]
        D --> E[Calculate Losses]
        E --> F[Save DuckDB + Parquet]
        style A fill:#ADD8E6
        style B fill:#ADD8E6
        style C fill:#87CEEB
        style D fill:#87CEEB
        style E fill:#4682B4,color:#fff
        style F fill:#90EE90
    '''
    mo.accordion({
        "## 📊 Analysis Workflow": mo.mermaid(workflow_diagram)
    })
    return


@app.cell
def _(mo):
    mo.md("## ⚙️ Analysis Configuration")
    return


@app.cell
def _(mo, os):
    # Default paths relative to the examples/ folder
    _notebook_dir = os.path.dirname(os.path.abspath(__file__))
    _examples_dir = os.path.dirname(_notebook_dir)
    default_examples_dir = _examples_dir
    default_outputs_dir = os.path.join(_examples_dir, "outputs")

    output_dir_input = mo.ui.file_browser(
        initial_path=_examples_dir,
        filetypes=None,
        selection_mode="directory",
        multiple=False,
        label="💾 Output Directory (click the folder icon to select)",
    )

    _tip = mo.md("""
    /// admonition | Tip
        type: attention

    Click the **FOLDER ICON** to the **LEFT** of the `outputs` directory to select it.
    A timestamped sub-folder will be created automatically for each run.
    ///
    """)

    mo.vstack([output_dir_input, _tip])
    return default_examples_dir, default_outputs_dir, output_dir_input


@app.cell
def _(default_examples_dir, mo):
    _default_buildings = os.path.join(
        default_examples_dir, "inputs", "buildings", "nsi2026_public_wkb.parquet"
    )

    building_file_selector = mo.ui.file_browser(
        initial_path=default_examples_dir,
        filetypes=[".parquet"],
        label="🏢 NSI 2026 Buildings Parquet File",
        multiple=False,
    )

    mo.vstack([
        mo.md("### 🏗️ Building Inventory"),
        mo.md("Select the NSI 2026 geoparquet buildings file."),
        building_file_selector,
    ])
    return (building_file_selector,)


@app.cell
def _(mo):
    import os as _os

    analysis_method_selector = mo.ui.dropdown(
        options={
            "HazusFloodAnalysis — Original HAZUS methodology (riverine/coastal)": "hazus1",
            "HazusFloodAnalysis2 — Updated methodology (velocity + duration riverine, CHW/CMV/CST coastal)": "hazus2",
        },
        value="HazusFloodAnalysis — Original HAZUS methodology (riverine/coastal)",
        label="🔬 Analysis Method",
    )

    flood_type_selector = mo.ui.dropdown(
        options={"Riverine (R)": "R", "Coastal (C)": "C"},
        value="Riverine (R)",
        label="🌊 Flood Type",
    )

    mo.vstack([
        mo.md("### 🔬 Analysis Method"),
        analysis_method_selector,
        flood_type_selector,
    ])
    return analysis_method_selector, flood_type_selector


@app.cell
def _(analysis_method_selector, default_examples_dir, mo):
    _is_hazus2 = analysis_method_selector.value == "hazus2"

    depth_raster_selector = mo.ui.file_browser(
        initial_path=default_examples_dir,
        filetypes=[".tif", ".tiff"],
        label="🌊 Depth Raster (required)",
        multiple=False,
    )

    velocity_raster_selector = mo.ui.file_browser(
        initial_path=default_examples_dir,
        filetypes=[".tif", ".tiff"],
        label="💨 Velocity Raster (optional — HazusFloodAnalysis2 only)",
        multiple=False,
    )

    duration_raster_selector = mo.ui.file_browser(
        initial_path=default_examples_dir,
        filetypes=[".tif", ".tiff"],
        label="⏱️ Duration Raster (optional — HazusFloodAnalysis2 only)",
        multiple=False,
    )

    _optional_rasters = mo.vstack([
        mo.md("*Velocity and duration rasters are used by HazusFloodAnalysis2 for riverine peril classification.*"),
        velocity_raster_selector,
        duration_raster_selector,
    ]) if _is_hazus2 else mo.md(
        "*Velocity and duration rasters are only used with HazusFloodAnalysis2.*"
    )

    mo.vstack([
        mo.md("### 🗺️ Hazard Rasters"),
        depth_raster_selector,
        _optional_rasters,
    ])
    return depth_raster_selector, duration_raster_selector, velocity_raster_selector


@app.cell
def _(mo):
    validate_button = mo.ui.run_button(label="✅ Validate Inputs")
    mo.vstack([
        mo.md("---"),
        mo.md("Click below to validate your configuration before running:"),
        validate_button,
    ])
    return (validate_button,)


@app.cell
def _(
    analysis_method_selector,
    building_file_selector,
    depth_raster_selector,
    duration_raster_selector,
    flood_type_selector,
    mo,
    os,
    output_dir_input,
    default_outputs_dir,
    validate_button,
    velocity_raster_selector,
):
    """Validate Configuration"""

    building_file = None
    depth_raster_file = None
    velocity_raster_file = None
    duration_raster_file = None
    analysis_method = analysis_method_selector.value
    flood_type = flood_type_selector.value
    config_valid = False

    if not validate_button.value:
        _display = mo.callout(
            mo.md("👆 **Click 'Validate Inputs' above** to check your configuration."),
            kind="info",
        )
    else:
        _issues = []

        # Building file
        if len(building_file_selector.value) == 0:
            _issues.append("No buildings parquet file selected.")
        else:
            building_file = building_file_selector.value[0].path
            if not os.path.isfile(building_file):
                _issues.append(f"Buildings file not found: `{building_file}`")

        # Depth raster
        if len(depth_raster_selector.value) == 0:
            _issues.append("No depth raster selected. A depth raster is required.")
        else:
            depth_raster_file = depth_raster_selector.value[0].path
            if not os.path.isfile(depth_raster_file):
                _issues.append(f"Depth raster not found: `{depth_raster_file}`")

        # Optional velocity/duration (HazusFloodAnalysis2 only)
        if analysis_method == "hazus2":
            if len(velocity_raster_selector.value) > 0:
                _v = velocity_raster_selector.value[0].path
                if os.path.isfile(_v):
                    velocity_raster_file = _v
            if len(duration_raster_selector.value) > 0:
                _d = duration_raster_selector.value[0].path
                if os.path.isfile(_d):
                    duration_raster_file = _d

        # Output directory
        if output_dir_input.value and len(output_dir_input.value) > 0:
            _output_base = str(output_dir_input.value[0].path)
        else:
            _output_base = default_outputs_dir

        config_valid = len(_issues) == 0

        if _issues:
            _display = mo.callout(
                mo.md("**Please fix the following issues:**\n\n" + "\n".join(f"- {i}" for i in _issues)),
                kind="danger",
            )
        else:
            _summary = [
                f"- **Analysis Method:** {analysis_method_selector.value.split('—')[0].strip()}",
                f"- **Flood Type:** {flood_type}",
                f"- **Buildings:** `{os.path.basename(building_file)}`",
                f"- **Depth Raster:** `{os.path.basename(depth_raster_file)}`",
            ]
            if velocity_raster_file:
                _summary.append(f"- **Velocity Raster:** `{os.path.basename(velocity_raster_file)}`")
            if duration_raster_file:
                _summary.append(f"- **Duration Raster:** `{os.path.basename(duration_raster_file)}`")
            _display = mo.callout(
                mo.md("✅ **Configuration valid!**\n\n" + "\n".join(_summary)),
                kind="success",
            )

    _display
    return (
        analysis_method,
        building_file,
        config_valid,
        depth_raster_file,
        duration_raster_file,
        flood_type,
        velocity_raster_file,
    )


@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="▶️ Run Analysis", kind="success")
    run_button
    return (run_button,)


@app.cell
def _(
    HazusFloodAnalysis,
    HazusFloodAnalysis2,
    DefaultFloodVulnerability,
    NsiBuildings2026,
    Path,
    SingleValueRaster,
    analysis_method,
    building_file,
    config_valid,
    default_outputs_dir,
    depth_raster_file,
    duckdb,
    duration_raster_file,
    flood_type,
    mo,
    os,
    output_dir_input,
    run_button,
    time,
    velocity_raster_file,
):
    """Execute Analysis"""

    mo.stop(
        not config_valid,
        mo.callout(mo.md("⚠️ Please complete the configuration above before running analysis."), kind="warn"),
    )
    mo.stop(not run_button.value, "")

    # Determine output directory
    if output_dir_input.value and len(output_dir_input.value) > 0:
        _output_base = str(output_dir_input.value[0].path)
    else:
        _output_base = default_outputs_dir

    # Create timestamped run directory
    _timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_output_dir = os.path.join(_output_base, _timestamp)
    os.makedirs(run_output_dir, exist_ok=True)

    duckdb_path = os.path.join(run_output_dir, "sphere_analysis.duckdb")
    parquet_path = os.path.join(run_output_dir, "sphere_results_wide.parquet")

    analysis_start = time.perf_counter()

    # Step 1: Load hazard rasters
    with mo.status.spinner(title="Loading hazard rasters..."):
        depth_grid = SingleValueRaster(depth_raster_file)
        velocity_grid = SingleValueRaster(velocity_raster_file) if velocity_raster_file else None
        duration_grid = SingleValueRaster(duration_raster_file) if duration_raster_file else None

        # Collect all supplied rasters; NsiBuildings2026 computes the union bbox.
        _all_rasters = [r for r in [depth_grid, velocity_grid, duration_grid] if r is not None]

    # Step 2: Load buildings filtered to the union bbox of all supplied rasters
    with mo.status.spinner(title="Loading buildings for study area..."):
        buildings = NsiBuildings2026(building_file, rasters=_all_rasters)
        _n_buildings = len(buildings.gdf)

    # Step 3: Set up vulnerability and analysis objects
    with mo.status.spinner(title="Initialising analysis..."):
        if analysis_method == "hazus1":
            vuln_func = DefaultFloodVulnerability(buildings, flood_type=flood_type)
            analyzer = HazusFloodAnalysis(
                buildings=buildings,
                vulnerability_func=vuln_func,
                depth_grid=depth_grid,
            )
        else:
            # HazusFloodAnalysis2 does not use a separate vulnerability wrapper
            analyzer = HazusFloodAnalysis2(
                buildings=buildings,
                depth_grid=depth_grid,
                flood_type=flood_type,
                velocity_grid=velocity_grid,
                duration_grid=duration_grid,
            )

    # Step 4: Run DuckDB analysis pipeline
    with mo.status.spinner(title="Running DuckDB flood loss pipeline..."):
        _db_start = time.perf_counter()
        # Remove existing duckdb file if present so we start fresh
        Path(duckdb_path).unlink(missing_ok=True)
        conn = duckdb.connect(duckdb_path)
        try:
            losses_df = analyzer.calculate_losses_duckdb(conn)
        finally:
            # Leave the file open reference but we close it after export
            pass
        _db_elapsed = time.perf_counter() - _db_start

    total_elapsed = time.perf_counter() - analysis_start

    mo.callout(
        mo.md(f"""
        ✅ **Analysis complete!**

        - Buildings in study area: **{_n_buildings:,}**
        - Flooded buildings: **{len(losses_df):,}**
        - DuckDB pipeline time: **{_db_elapsed:.1f}s**
        - Total time: **{total_elapsed:.1f}s**
        """),
        kind="success",
    )
    return (
        conn,
        duckdb_path,
        losses_df,
        parquet_path,
        run_output_dir,
        total_elapsed,
    )


@app.cell
def _(conn, duckdb_path, losses_df, mo, parquet_path, run_output_dir):
    """Export Results"""

    with mo.status.spinner(title="Exporting results..."):
        # Build wide parquet by joining buildings + losses inside DuckDB
        wide_df = conn.execute("""
            SELECT
                b.*,
                l.building_loss,
                l.content_loss,
                l.inventory_loss
            FROM buildings b
            LEFT JOIN losses l ON b.id = l.id
        """).fetchdf()

        # Write wide parquet
        wide_df.to_parquet(parquet_path, compression="zstd", index=False)

        # Close DuckDB connection — the file at duckdb_path is now fully written
        conn.close()

    _total_loss = losses_df["building_loss"].sum() if "building_loss" in losses_df.columns else 0
    _buildings_with_loss = (losses_df["building_loss"] > 0).sum() if "building_loss" in losses_df.columns else 0

    mo.vstack([
        mo.md("## 📁 Output Files"),
        mo.callout(
            mo.md(f"""
            Both files saved to `{run_output_dir}`:

            - **`sphere_results_wide.parquet`** — {len(wide_df):,} buildings, all columns ({len(wide_df.columns)} fields)
            - **`sphere_analysis.duckdb`** — intermediate DuckDB database with all analysis tables
            """),
            kind="success",
        ),
    ])
    return wide_df, _total_loss, _buildings_with_loss


@app.cell
def _(losses_df, mo, wide_df, _total_loss, _buildings_with_loss):
    """Summary Statistics"""

    mo.vstack([
        mo.md("## 📊 Results Summary"),
        mo.hstack([
            mo.stat(
                label="Buildings in Study Area",
                value=f"{len(wide_df):,}",
                caption="loaded from parquet",
            ),
            mo.stat(
                label="Flooded Buildings",
                value=f"{len(losses_df):,}",
                caption=f"{len(losses_df) / max(len(wide_df), 1) * 100:.1f}% of total",
                bordered=True,
            ),
            mo.stat(
                label="Total Building Loss",
                value=f"${_total_loss:,.0f}",
                caption="sum across flooded buildings",
                bordered=True,
            ),
            mo.stat(
                label="Buildings with Loss > 0",
                value=f"{_buildings_with_loss:,}",
                caption=f"{_buildings_with_loss / max(len(losses_df), 1) * 100:.1f}% of flooded",
            ),
        ], justify="space-around"),
        mo.md("### 🔍 Loss Preview (first 100 rows)"),
        losses_df.head(100),
    ])
    return


if __name__ == "__main__":
    app.run()
