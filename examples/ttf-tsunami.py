import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium")

with app.setup:
    # Initialization code that runs before all other cells
    import marimo as mo
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point
    from pathlib import Path
    from sphere.core.schemas.buildings import ttfBuildings
    from sphere.tsunami.analysis.ttf_aal_analysis import ttfAALAnalysis
    from sphere.tsunami.default_vulnerability import DefaultTsunamiVulnerability


@app.cell
def _():
    # Display all the csv files in the tsunami_transform_function folder
    folder_path = Path("./tests/data/new")  # Change this to your folder path
    _csv_files = sorted([f.name for f in folder_path.glob("*.csv")])

    form = mo.md(
        """
        ## Parameters\n
        \n
        ### Select CSV file: {csv_select}\n
        ### Building Loss Deductible: {bldg_deductible}\n
        ### Building Loss Cap: {bldg_cap}\n
        ### Content Loss Deductible: {cont_deductible}\n
        ### Content Loss Cap: {cont_cap}\n
        """
                ).batch(
        csv_select = mo.ui.dropdown(
            label="Select CSV file:",
            options=_csv_files,
            value=None,
        ),
        bldg_deductible = mo.ui.number(5_000),
        bldg_cap = mo.ui.number(250_000),
        cont_deductible = mo.ui.number(1_250),
        cont_cap = mo.ui.number(100_000),
    ).form()
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
    results[['NsiID', 'EqBldgType', 'EqDesignLe', 'ValStruct', 'ValCont', 'building_loss_aal', 'content_loss_aal', 'gross_building_loss_aal', 'gross_content_loss_aal', 'building_loss_10y', 'building_loss_25y', 'building_loss_50y', 'building_loss_72y', 'building_loss_100y', 'building_loss_150y', 'building_loss_200y', 'building_loss_250y', 'building_loss_475y', 'building_loss_750y', 'building_loss_975y', 'building_loss_1500y', 'building_loss_2475y', 'building_loss_3000y']]
    return


@app.cell
def _(form):
    # Create the form
    export_form = (
        mo.md('''
        **Export Results to CSV**

        {filename}
        ''')
        .batch(
            filename=mo.ui.text(
                label="CSV Filename",
                placeholder="Enter filename (without .csv)"
            )
        )
        .form(bordered=True, label="Export")
    )

    export_form if form.value else mo.md('Run analysis first.')
    return (export_form,)


@app.cell
def _(export_form, results):
    if export_form.value and export_form.value["filename"]:
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
