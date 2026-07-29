import marimo

__generated_with = "0.23.15"
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
        DefaultFloodVulnerability,
        HazusFloodAnalysis,
        HazusFloodAnalysis2,
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

    Select one or more depth rasters to analyse multiple flood scenarios in a single run.
    Each raster produces its own interim DuckDB file; all results are merged into one wide parquet.
    ///

    [Documentation](https://github.com/Niyam-Projects/sphere) | [HAZUS Methodology](https://www.fema.gov/flood-maps/products-tools/hazus)
    """)
    return


@app.cell
def _(mo):
    workflow_diagram = '''
    graph LR
        A[Load Buildings] --> B[Load Depth Rasters]
        B --> C[Filter to Union Bbox]
        C --> D[For Each Raster]
        D --> E[DuckDB Analysis]
        E --> F[Per-Raster DuckDB]
        F --> G[Merge Wide Parquet]
        style A fill:#ADD8E6
        style B fill:#ADD8E6
        style C fill:#87CEEB
        style D fill:#87CEEB
        style E fill:#4682B4,color:#fff
        style F fill:#4682B4,color:#fff
        style G fill:#90EE90
    '''
    mo.accordion({
        "## 📊 Analysis Workflow": mo.mermaid(workflow_diagram)
    })
    return


@app.cell
def _(mo):
    mo.md("""
    ## ⚙️ Analysis Configuration
    """)
    return


@app.cell
def _(mo, os):
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
    A timestamped sub-folder is created automatically for each run.
    ///
    """)

    mo.vstack([output_dir_input, _tip])
    return default_examples_dir, default_outputs_dir, output_dir_input


@app.cell
def _(default_examples_dir, mo):
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
def _(analysis_method_selector, default_examples_dir, mo, os):
    _is_hazus2 = analysis_method_selector.value == "hazus2"

    depth_raster_selector = mo.ui.file_browser(
        initial_path=os.path.join(default_examples_dir, "inputs", "rasters"),
        filetypes=[".tif", ".tiff"],
        label="🌊 Depth Rasters — select one or more (required)",
        multiple=True,
    )

    velocity_raster_selector = mo.ui.file_browser(
        initial_path=os.path.join(default_examples_dir, "inputs", "rasters"),
        filetypes=[".tif", ".tiff"],
        label="💨 Velocity Raster (optional — HazusFloodAnalysis2 only, shared across all depth rasters)",
        multiple=False,
    )

    duration_raster_selector = mo.ui.file_browser(
        initial_path=os.path.join(default_examples_dir, "inputs", "rasters"),
        filetypes=[".tif", ".tiff"],
        label="⏱️ Duration Raster (optional — HazusFloodAnalysis2 only, shared across all depth rasters)",
        multiple=False,
    )

    _optional_rasters = mo.vstack([
        mo.md("*Velocity and duration rasters are shared across all selected depth rasters.*"),
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
    return (
        depth_raster_selector,
        duration_raster_selector,
        velocity_raster_selector,
    )


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
    validate_button,
    velocity_raster_selector,
):
    """Validate Configuration"""

    building_file = None
    depth_raster_files = []
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

        # Depth rasters (one or more required)
        if len(depth_raster_selector.value) == 0:
            _issues.append("No depth rasters selected. At least one depth raster is required.")
        else:
            for _item in depth_raster_selector.value:
                if os.path.isfile(_item.path):
                    depth_raster_files.append(_item.path)
                else:
                    _issues.append(f"Depth raster not found: `{_item.path}`")

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

        config_valid = len(_issues) == 0 and len(depth_raster_files) > 0

        if _issues:
            _display = mo.callout(
                mo.md("**Please fix the following issues:**\n\n" + "\n".join(f"- {i}" for i in _issues)),
                kind="danger",
            )
        else:
            _depth_names = ", ".join(f"`{os.path.basename(f)}`" for f in depth_raster_files)
            _summary = [
                f"- **Analysis Method:** {analysis_method_selector.value.split('—')[0].strip()}",
                f"- **Flood Type:** {flood_type}",
                f"- **Buildings:** `{os.path.basename(building_file)}`",
                f"- **Depth Rasters ({len(depth_raster_files)}):** {_depth_names}",
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
        depth_raster_files,
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
    DefaultFloodVulnerability,
    HazusFloodAnalysis,
    HazusFloodAnalysis2,
    NsiBuildings2026,
    Path,
    SingleValueRaster,
    analysis_method,
    building_file,
    config_valid,
    default_outputs_dir,
    depth_raster_files,
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
    """Execute Analysis — one DuckDB run per depth raster"""

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

    parquet_path = os.path.join(run_output_dir, "sphere_results_wide.parquet")

    analysis_start = time.perf_counter()

    # Step 1: Load all rasters up front
    with mo.status.spinner(title="Loading hazard rasters..."):
        depth_grids = [SingleValueRaster(f) for f in depth_raster_files]
        velocity_grid = SingleValueRaster(velocity_raster_file) if velocity_raster_file else None
        duration_grid = SingleValueRaster(duration_raster_file) if duration_raster_file else None

        # Union bbox across all rasters for building pre-filter
        _all_rasters = depth_grids + [r for r in [velocity_grid, duration_grid] if r is not None]

    # Step 2: Load buildings once, filtered to the union bbox of all rasters
    with mo.status.spinner(title="Loading buildings for study area..."):
        buildings = NsiBuildings2026(building_file, rasters=_all_rasters)
        _n_buildings = len(buildings.gdf)

    # Step 3: Run DuckDB analysis for each depth raster — separate .duckdb per raster
    # results_by_raster: {raster_stem: (losses_df, duckdb_path, elapsed_s)}
    results_by_raster = {}

    for _depth_grid in depth_grids:
        _stem = Path(_depth_grid.data_source).stem
        _duckdb_path = os.path.join(run_output_dir, f"sphere_analysis_{_stem}.duckdb")

        with mo.status.spinner(title=f"Running DuckDB analysis: {_stem}..."):
            _db_start = time.perf_counter()
            Path(_duckdb_path).unlink(missing_ok=True)
            _conn = duckdb.connect(_duckdb_path)

            if analysis_method == "hazus1":
                _vuln = DefaultFloodVulnerability(buildings, flood_type=flood_type)
                _analyzer = HazusFloodAnalysis(
                    buildings=buildings,
                    vulnerability_func=_vuln,
                    depth_grid=_depth_grid,
                )
            else:
                _analyzer = HazusFloodAnalysis2(
                    buildings=buildings,
                    depth_grid=_depth_grid,
                    flood_type=flood_type,
                    velocity_grid=velocity_grid,
                    duration_grid=duration_grid,
                )

            _losses = _analyzer.calculate_losses_duckdb(_conn)
            _conn.close()
            _elapsed = time.perf_counter() - _db_start

        results_by_raster[_stem] = (_losses, _duckdb_path, _elapsed)

    total_elapsed = time.perf_counter() - analysis_start

    # Build completion summary
    _summary_rows = "\n".join(
        f"  - **`{s}`** — {len(ldf):,} flooded buildings, "
        f"${ldf['building_loss'].sum():,.0f} building loss ({el:.1f}s)"
        for s, (ldf, _, el) in results_by_raster.items()
    )

    mo.callout(
        mo.md(
            f"✅ **Analysis complete!**\n\n"
            f"- Buildings in study area: **{_n_buildings:,}**\n"
            f"- Rasters analysed: **{len(results_by_raster)}**\n"
            + _summary_rows
            + f"\n- Total time: **{total_elapsed:.1f}s**"
        ),
        kind="success",
    )
    return buildings, parquet_path, results_by_raster, run_output_dir


@app.cell
def _(buildings, mo, parquet_path, pd, results_by_raster, run_output_dir):
    """Export Results — aggregate losses across all rasters into one wide parquet"""

    with mo.status.spinner(title="Exporting wide parquet..."):
        # Start from the buildings GeoDataFrame (geometry excluded)
        _bdf = buildings.gdf.drop(columns=["geometry"], errors="ignore")

        # Collect per-raster loss DataFrames and union all flooded building IDs
        _all_losses = []
        for _stem, (_losses_df, _duckdb_path, _elapsed) in results_by_raster.items():
            _all_losses.append(_losses_df[["id", "building_loss", "content_loss", "inventory_loss"]])

        # Sum losses across all rasters per building
        if _all_losses:
            _combined = pd.concat(_all_losses)
            _agg = (
                _combined
                .groupby("id", as_index=False)[["building_loss", "content_loss", "inventory_loss"]]
                .sum()
            )
            _agg["total_loss"] = (
                _agg["building_loss"] + _agg["content_loss"] + _agg["inventory_loss"]
            )
        else:
            _agg = pd.DataFrame(
                columns=["id", "building_loss", "content_loss", "inventory_loss", "total_loss"]
            )

        wide_df = _bdf.merge(_agg, left_on="fd_id", right_on="id", how="left").drop(
            columns=["id"], errors="ignore"
        )
        # Fill buildings with no loss as 0
        for _col in ["building_loss", "content_loss", "inventory_loss", "total_loss"]:
            wide_df[_col] = wide_df[_col].fillna(0)

        wide_df.to_parquet(parquet_path, compression="zstd", index=False)

    _duckdb_list = "\n".join(
        f"  - **`sphere_analysis_{s}.duckdb`**" for s in results_by_raster
    )

    mo.vstack([
        mo.md("## 📁 Output Files"),
        mo.callout(
            mo.md(
                f"All files saved to `{run_output_dir}`:\n\n"
                f"- **`sphere_results_wide.parquet`** — {len(wide_df):,} buildings, "
                f"{len(wide_df.columns)} columns "
                f"(building_loss, content_loss, inventory_loss, total_loss summed across all rasters)\n"
                + _duckdb_list
            ),
            kind="success",
        ),
    ])
    return (wide_df,)


@app.cell
def _(mo, pd, results_by_raster, wide_df):
    """Summary Statistics"""

    # Overall totals from the wide parquet (summed across rasters)
    _total_building = wide_df["building_loss"].sum() if "building_loss" in wide_df.columns else 0
    _total_content  = wide_df["content_loss"].sum()  if "content_loss"  in wide_df.columns else 0
    _total_inventory = wide_df["inventory_loss"].sum() if "inventory_loss" in wide_df.columns else 0
    _grand_total    = wide_df["total_loss"].sum()     if "total_loss"     in wide_df.columns else 0
    _n_with_loss    = int((wide_df["total_loss"] > 0).sum()) if "total_loss" in wide_df.columns else 0

    _overall_cards = mo.hstack([
        mo.stat(
            label="Total Buildings",
            value=f"{len(wide_df):,}",
            caption="in study area",
        ),
        mo.stat(
            label="Buildings with Loss",
            value=f"{_n_with_loss:,}",
            caption=f"{_n_with_loss / max(len(wide_df), 1) * 100:.1f}% of total",
            bordered=True,
        ),
        mo.stat(
            label="Total Building Loss",
            value=f"${_total_building:,.0f}",
            caption="summed across all rasters",
            bordered=True,
        ),
        mo.stat(
            label="Grand Total Loss",
            value=f"${_grand_total:,.0f}",
            caption="building + content + inventory",
            bordered=True,
        ),
    ], justify="space-around")

    # Per-raster breakdown table
    _scenario_rows = []
    for _stem, (_losses_df, _dpath, _elapsed) in results_by_raster.items():
        _b = _losses_df["building_loss"].sum() if "building_loss" in _losses_df.columns else 0
        _c = _losses_df["content_loss"].sum()  if "content_loss"  in _losses_df.columns else 0
        _iv = _losses_df["inventory_loss"].sum() if "inventory_loss" in _losses_df.columns else 0
        _scenario_rows.append({
            "Scenario": _stem,
            "Flooded Buildings": f"{len(_losses_df):,}",
            "Building Loss ($)": f"${_b:,.0f}",
            "Content Loss ($)":  f"${_c:,.0f}",
            "Inventory Loss ($)": f"${_iv:,.0f}",
            "Total Loss ($)":    f"${_b + _c + _iv:,.0f}",
            "Runtime (s)":       f"{_elapsed:.1f}",
        })
    # Totals row
    _scenario_rows.append({
        "Scenario": "── TOTAL ──",
        "Flooded Buildings": "",
        "Building Loss ($)": f"${_total_building:,.0f}",
        "Content Loss ($)":  f"${_total_content:,.0f}",
        "Inventory Loss ($)": f"${_total_inventory:,.0f}",
        "Total Loss ($)":    f"${_grand_total:,.0f}",
        "Runtime (s)":       "",
    })
    _summary_df = pd.DataFrame(_scenario_rows)

    mo.vstack([
        mo.md("## 📊 Results Summary"),
        _overall_cards,
        mo.md("### Loss Breakdown by Scenario"),
        mo.ui.table(_summary_df, selection=None),
    ])
    return


if __name__ == "__main__":
    app.run()
