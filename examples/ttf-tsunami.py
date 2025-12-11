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
    folder_path = Path("./examples/tsunami_transform_function")  # Change this to your folder path
    _csv_files = sorted([f.name for f in folder_path.glob("*.csv")])


    form = mo.ui.dropdown(
        label="Select CSV file:",
        options=_csv_files,
        value=None,
    ).form()
    form
    return folder_path, form


@app.cell
def _(folder_path, form):
    mo.stop(form.value is None, "Please select a CSV file to continue")
    _csv_file = folder_path / form.value
    _df = pd.read_csv(_csv_file)

    # Create geometry from X, Y coordinates
    _geometry = [Point(xy) for xy in zip(_df['Longitude'], _df['Latitude'])]
    gdf = gpd.GeoDataFrame(_df, geometry=_geometry, crs="EPSG:4326")

    buildings = ttfBuildings(gdf=gdf)
    analysis = ttfAALAnalysis(
        buildings=buildings,
        vulnerability_func=DefaultTsunamiVulnerability(),
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
