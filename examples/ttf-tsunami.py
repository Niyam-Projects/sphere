import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")

with app.setup:
    # Initialization code that runs before all other cells
    import marimo as mo
    import re
    import geopandas as gpd
    import pandas as pd
    from datetime import datetime
    from shapely.geometry import Point
    from pathlib import Path
    from sphere.core.schemas.buildings import ttfBuildings
    from sphere.tsunami.analysis.ttf_aal_analysis import ttfAALAnalysis
    from sphere.tsunami.default_vulnerability import DefaultTsunamiVulnerability


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _():
    import importlib.metadata
    try:
        __sphere_version__ = importlib.metadata.version("niyamit-sphere")
        __tsunami_version__ = importlib.metadata.version("tsunami")
    except importlib.metadata.PackageNotFoundError:
        # Handle the case where the package is not installed
        __sphere_version__ = "unknown"
        __tsunami_version__ = "unknown"

    _sphere_msg = f"SPHERE version: {__sphere_version__}"
    _tsunami_msg = f"Tsunami version: {__tsunami_version__}"

    mo.vstack([
        mo.md(_sphere_msg),
        mo.md(_tsunami_msg),
    ])
    return (__sphere_version__,)


@app.cell
def _():
    # Display all the csv files in the tsunami_transform_function folder
    folder_path = Path("./examples/tsunami_transform_function/")  # Change this to your folder path
    _csv_files = sorted([f.name for f in folder_path.glob("*.csv")])

    form = mo.md(
        """
        ### Select CSV file: {csv_select}\n
        ### Building Loss Deductible: {bldg_deductible}\n
        ### Building Loss Cap: {bldg_cap}\n
        ### Content Loss Deductible: {cont_deductible}\n
        ### Content Loss Cap: {cont_cap}\n
        """
                ).batch(
        csv_select = mo.ui.dropdown(
            options=_csv_files,
            value=None,
        ),
        bldg_deductible = mo.ui.number(5_000),
        bldg_cap = mo.ui.number(250_000),
        cont_deductible = mo.ui.number(1_250),
        cont_cap = mo.ui.number(100_000),
    ).form(bordered=True, label="## **Parameters**")
    form
    return folder_path, form


@app.cell
def _(folder_path, form):
    mo.stop(form.value is None or form.value["csv_select"] is None, "Please select a CSV file to continue")

    _csv_file = mo.cli_args().get("file") or folder_path / form.value["csv_select"]
    if mo.running_in_notebook:
        _bldg_deductible = int(form.value["bldg_deductible"])
        _bldg_cap = int(form.value["bldg_cap"])
        _cont_deductible = int(form.value["cont_deductible"])
        _cont_cap = int(form.value["cont_cap"])

    else:
        _bldg_deductible = int(mo.cli_args().get("bldg_deductible") or 5_000)
        _bldg_cap = int(mo.cli_args().get("bldg_cap") or 250_000)
        _cont_deductible = int(mo.cli_args().get("cont_deductible") or 1_250)
        _cont_cap = int(mo.cli_args().get("cont_cap") or 100_000)
    _df = pd.read_csv(_csv_file)

    # Create geometry from X, Y coordinates
    _geometry = [Point(xy) for xy in zip(_df['Longitude'], _df['Latitude'])]
    gdf = gpd.GeoDataFrame(_df, geometry=_geometry, crs="EPSG:4326")

    buildings = ttfBuildings(gdf=gdf)
    analysis = ttfAALAnalysis(
        buildings=buildings,
        vulnerability_func=DefaultTsunamiVulnerability(),
        bldg_deductible = _bldg_deductible,
        bldg_cap = _bldg_cap,
        cont_deductible = _cont_deductible,
        cont_cap = _cont_cap,
    )

    results = analysis.calculate_losses()

    gdf
    return (results,)


@app.cell
def _(results):
    # 1. Define the base loss categories to aggregate
    _loss_categories = [
        "building_loss", "content_loss", "inventory_loss",
        "wage_loss", "rental_loss", "relocation_loss", "income_loss",
    ]

    # 2. Extract unique return periods as integers for numeric sorting
    _period_map = {}
    for _col in results.columns:
        # Matches 'MomFlux_' followed by digits and then 'y'
        _match = re.search(r"MomFlux_(\d+)y", _col)
        if _match:
            _years = int(_match.group(1))
            # Map the integer years to the standardized suffix string
            _period_map[_years] = f"_{_years}y"

    # 3. Iterate through sorted integers to ensure numeric order (e.g., 25, 50, 100, 2500)
    for _years in sorted(_period_map.keys()):
        _sfx = _period_map[_years]

        # Identify columns that exist for this specific return period
        _cols_to_sum = [
            f"{_cat}{_sfx}" for _cat in _loss_categories 
            if f"{_cat}{_sfx}" in results.columns
        ]

        if _cols_to_sum:
            # Vectorized sum added to the GeoDataFrame
            _target_col_name = f"total_economic_loss{_sfx}"
            results[_target_col_name] = results[_cols_to_sum].sum(axis=1)
    return


@app.cell
def _(form):
    mo.stop(form.value is None or form.value["csv_select"] is None)
    columns_form = mo.md(
        """
        ### View Columns: {cols_select}\n
        """
                ).batch(
        cols_select = mo.ui.dropdown(
            options=[
                "total_economic_loss",
                "building_loss",
                "content_loss",
                "inventory_loss",
                "wage_loss",
                "rental_loss",
                "relocation_loss",
                "income_loss",
            ],
            value="total_economic_loss",
            allow_select_none=False,
        ),
    ).form(bordered=True, label="## **Select Loss Columns for View**")
    columns_form
    return (columns_form,)


@app.cell
def _(columns_form, results):
    view_columns = ['NsiID', 'EqBldgType', 'EqDesignLe', 'ValStruct', 'ValCont']
    if columns_form.value:
        cols_to_add = [col for col in list(results.columns.values) if columns_form.value["cols_select"] in col]
    else:
        cols_to_add = [col for col in list(results.columns.values) if "building_loss" in col]
    view_columns += cols_to_add
    results[view_columns]
    return


@app.cell
def _(__sphere_version__, form):
    # Create the form
    _current_date = datetime.now().strftime("%Y%m%d")
    form
    export_form = (
        mo.md('''
        {filename}
        ''')
        .batch(
            filename=mo.ui.text(
                label="CSV Filename",
                value=f"results_{_current_date}_v{__sphere_version__.replace('.', '_')}",
                placeholder="Enter filename (without .csv)"
            )
        )
        .form(bordered=True, label="## **Export Results to CSV**")
    )

    export_form if form.value else mo.md('Run analysis first.')
    return (export_form,)


@app.cell
def _(export_form, results):
    if export_form.value and export_form.value["filename"]:
        with mo.status.spinner(subtitle="Saving csv file ...") as _spinner:
            # Get the filename from the form
            filename = export_form.value["filename"]

            # Ensure .csv extension
            if not filename.endswith('.csv'):
                filename += '.csv'

            # Create outputs folder if it doesn't exist
            output_dir = Path('outputs')
            output_dir.mkdir(exist_ok=True)

            # Full path for the CSV file
            output_path = output_dir / filename

            # Export the GeoDataFrame to CSV
            results.to_csv(output_path, index=False)

        # Show success message
        result = mo.md(f"✅ Successfully exported to `{output_path}`")
    else:
        result = mo.md("Enter a filename and click Export")

    result
    return


if __name__ == "__main__":
    app.run()
