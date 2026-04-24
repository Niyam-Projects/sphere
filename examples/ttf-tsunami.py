import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")

with app.setup:
    # Initialization code that runs before all other cells
    import logging
    import marimo as mo
    import re
    import geopandas as gpd
    import pandas as pd
    from datetime import datetime
    from io import BytesIO
    from io import StringIO
    from contextlib import redirect_stdout
    from contextlib import redirect_stderr
    from shapely.geometry import Point
    from pathlib import Path
    from sphere.core.schemas.buildings import ttfBuildings
    from sphere.tsunami.analysis.ttf_aal_analysis import ttfAALAnalysis
    from sphere.tsunami.default_vulnerability import DefaultTsunamiVulnerability

    import os
    import sys
    os.makedirs('./outputs/logs', exist_ok=True)
    _LOG_FILE = os.path.abspath(f'./outputs/logs/{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

    logging.basicConfig(
        # filename=_LOG_FILE,
        level=logging.INFO,
        force=True,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(_LOG_FILE),
            logging.StreamHandler()
        ],
    )


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


@app.cell(hide_code=True)
def _():
    column_dict = {
        "PRIMARY KEY": [
            "ID",
            "NsiID",
        ],
        "INVENTORY": [
            "EqBldgType",
            "EqDesignLe",
            "SOccupID",
            "Occupancy_Type",
            "FirstFloor",
            "ValStruct",
            "ValCont",
            "AreaSqft",
            "CBFips",
            "geometry",
            "Longitude",
            "Latitude",
            "Point",
        ],
        "HAZARD": [
            "FlowDepth_*yr_Median_ft",
            "Speed_*yr_Median_ft_per_sec",
            "MomFlux_*yr_Median_ft_per_sec",
            "First_Wet_RP_yrs",
            "Site_Elevation_ft",
            "Grid_Index",
            "AnchorPt_Index",
            "depth_in_structure_*y",
        ],
        "DAMAGE STATE PROBABILITIES": [
            "p_str_comp_*y",
            "p_str_ext_*y",
            "p_str_mod_*y",
            "p_str_none_*y",
            "p_nsd_comp_*y",
            "p_nsd_ext_*y",
            "p_nsd_mod_*y",
            "p_nsd_none_*y",
            "p_cont_comp_*y",
            "p_cont_ext_*y",
            "p_cont_mod_*y",
            "p_cont_none_*y",
        ],
        "ANALYSIS PARAMETERS": [
            "Occupancy",
            "SlightStrRepair",
            "ModStrRepair",
            "ExtStrRepair",
            "CmpStrRepair",
            "SlightNsaRepair",
            "ModNsaRepair",
            "ExtNsaRepair",
            "CmpNsaRepair",
            "SlightNsdRepair",
            "ModNsdRepair",
            "ExtNsdRepair",
            "CmpNsdRepair",
            "SlightCntRepair",
            "ModCntRepair",
            "ExtCntRepair",
            "CmpCntRepair",
            "NoneRepairTime",
            "SlightRepairTime",
            "ModRepairTime",
            "ExtRepairTime",
            "CmpRepairTime",
            "NoneRecoveryTime",
            "SlightRecoveryTime",
            "ModRecoveryTime",
            "ExtRecoveryTime",
            "CmpRecoveryTime",
            "NoneConstrTime",
            "SlightConstrTime",
            "ModConstrTime",
            "ExtConstrTime",
            "CmpConstrTime",
            "RentPerDay",
            "RentPerMonth",
            "DisruptCostPerMonth",
            "PctOwnerOcc",
            "IncPerDay",
            "IncPerYear",
            "WagePerDay",
            "EmployeePerSqft",
            "OutputPerDay",
            "WageRecap",
            "EmploymentRecap",
            "IncomeRecap",
            "OutputRecap",
            "Occupancy_econInc",
            "GrossSales",
            "BusinessInv",
            "SlightInvDmg",
            "ModInvDmg",
            "ExtInvDmg",
            "CmpInvDmg",
        ],
        "LOSSES (RETURN PERIOD)": [
            "StructLoss_*y",
            "NonStrLoss_*y",
            "building_loss_*y",
            "content_loss_*y",
            "inventory_loss_*y",
            "relocation_loss_*y",
            "income_loss_*y",
            "rental_loss_*y",
            "wage_loss_*y",
            "total_economic_loss_*y",
        ],
        "LOSSES (AVERAGE ANNUALIZED LOSS)": [
            "building_loss_aal",
            "BldgAAL_LossRatio_USDperM",
            "content_loss_aal",
            "inventory_loss_aal",
            "relocation_loss_aal",
            "income_loss_aal",
            "rental_loss_aal",
            "wage_loss_aal",
            "CapitalLoss_AAL",
            "IncomeLoss_AAL",
            "TotalEconomicLoss_AAL",
        ],
        "LOSSES (ACTUARIAL LOSS)": [
            "gross_building_loss_*y",
            "gross_content_loss_*y",
            "gross_building_loss_aal",
            "GrossBldgAAL_LossRatio_USDperM",
            "gross_content_loss_aal",
        ],
    }
    return (column_dict,)


@app.function(hide_code=True)
def reorder_columns(df, column_order):
    # Build a lowercased lookup of actual df columns for exact matching
    lower_to_actual = {c.lower(): c for c in df.columns}

    matched_columns = []

    for col in column_order:
        if '*' in col:
            pattern = re.compile('^' + re.escape(col).replace(r'\*', '.*') + '$', re.IGNORECASE)
            matches = [c for c in df.columns if pattern.match(c)]
            matched_columns.extend(matches)
        elif col.lower() in lower_to_actual:
            matched_columns.append(lower_to_actual[col.lower()])

    return df[matched_columns]


@app.cell
def _():
    # Display all the csv files in the tsunami_transform_function folder
    folder_path = Path(r"./examples/tsunami_transform_function/")  # Change this to your folder path

    form = mo.md(
        """
        ### {csv_select}\n
        ### Building Loss Deductible: {bldg_deductible}\n
        ### Building Loss Cap: {bldg_cap}\n
        ### Content Loss Deductible: {cont_deductible}\n
        ### Content Loss Cap: {cont_cap}\n
        """
                ).batch(
        csv_select = mo.ui.file(
            label="Upload CSV File",
            filetypes=[".csv"],
            multiple=False,
        ),
        bldg_deductible = mo.ui.number(5_000),
        bldg_cap = mo.ui.number(250_000),
        cont_deductible = mo.ui.number(1_250),
        cont_cap = mo.ui.number(100_000),
    ).form(bordered=True, label="## **Parameters**")
    form
    return (form,)


@app.cell
def _(column_dict, form):
    mo.stop(form.value is None or form.value["csv_select"] is None, "Please select a CSV file to continue")
    with mo.redirect_stderr():
        try:
            # _csv_file = mo.cli_args().get("file") or folder_path / form.value["csv_select"]
            _csv_file = mo.cli_args().get("file") or form.value["csv_select"][0].contents
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
            _df = pd.read_csv(BytesIO(_csv_file))

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

            # Reorder the fields
            _col_order = [_col for _cols in column_dict.values() for _col in _cols]
            results = reorder_columns(results, _col_order)
            success = True
        except Exception as _e:
            success = False
    return gdf, results, success


@app.cell
def _(gdf, success):
    mo.stop(not success)
    gdf
    return


@app.cell
def _(results, success):
    mo.stop(not success)
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
def _(column_dict, form, success):
    mo.stop(form.value is None or form.value["csv_select"] is None or not success)
    cols_select = mo.ui.dropdown(
        options=list(column_dict.keys())[1:],
        value=list(column_dict.keys())[1],
        allow_select_none=False,
    )
    mo.vstack([
        mo.md("# View Domains"),
        cols_select,
    ])
    return (cols_select,)


@app.cell
def _(cols_select, column_dict, results, success):
    mo.stop(not success)
    # view_columns = ['NsiID', 'EqBldgType', 'EqDesignLe', 'ValStruct', 'ValCont']
    reorder_columns(results, column_dict["PRIMARY KEY"] + column_dict[cols_select.value])
    # results[view_columns]
    return


@app.cell
def _(__sphere_version__, column_dict, form, success):
    # Create the form
    _current_date = datetime.now().strftime("%Y%m%d")
    export_form = (
        mo.md('''
        {filename}\n
        {cols}
        ''')
        .batch(
            filename=mo.ui.text(
                label="CSV Filename",
                value=f"results_{_current_date}_v{__sphere_version__.replace('.', '_')}",
                placeholder="Enter filename (without .csv)"
            ),
            cols = mo.ui.multiselect(
                label="Select Domains",
                options=list(column_dict.keys())[1:],
                # value=[list(column_dict.keys())[1]],
            ),
        )
        .form(bordered=True, label="## **Export Results to CSV**")
    )
    export_form if form.value and success else mo.md('Run analysis first.')
    return (export_form,)


@app.cell
def _(column_dict, export_form, results, success):
    if export_form.value and success and export_form.value["filename"]:
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
            _filtered_dict = {_k: column_dict[_k] for _k in export_form.value["cols"]}
            _col_order = [_col for _cols in _filtered_dict.values() for _col in _cols]
            _final_results = reorder_columns(results, column_dict["PRIMARY KEY"] + _col_order)
            _final_results.to_csv(output_path, index=False)

        # Show success message
        result = mo.md(f"✅ Successfully exported to `{output_path}`")
    else:
        result = mo.md("Enter a filename and click Submit")

    result
    return


@app.cell
def _():
    def _val_track(val):
        if not val:
            val += 1
        else:
            val -= 1
        return val
    show_datadict_button = mo.ui.button(
        label="Click to toggle Data Dictionary",
        value=0,
        on_click=lambda value: _val_track(value)
    )
    show_datadict_button
    return (show_datadict_button,)


@app.cell
def _(show_datadict_button):
    if show_datadict_button.value:
        _md_file = "Tsunami_DataDictionary.md"
        with open(_md_file, "r") as _f:
            _content = _f.read()
        _display = mo.md(_content)
    else:
        _display = mo.md("")
    _display
    return


if __name__ == "__main__":
    app.run()
