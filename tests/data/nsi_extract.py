# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "duckdb==1.4.2",
#     "polars[pyarrow]==1.35.2",
#     "sqlglot==28.0.0",
# ]
# ///

import marimo

__generated_with = "0.17.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Make sure to run this notebook using uvx and --sandbox so that there isn't things added to this repo.
    """)
    return


@app.cell
def _():
    return


@app.cell
def _(mo):
    nsi_results_df = mo.sql(
        f"""
        INSTALL spatial;
        LOAD spatial;
        SELECT * EXCLUDE(geom) FROM ST_READ("E:\projects\CalOES\output\R_19_San_Francisco_rp3000_sl2p0_maxFLOWDEPTH.gpkg", layer="nsi_buildings_results")
            WHERE ST_X(geom) BETWEEN -122.378193 AND -122.371998
          	AND ST_Y(geom) BETWEEN 37.822905 AND 37.829772;
        """,
        output=False
    )
    return (nsi_results_df,)


@app.cell
def _(nsi_results_df):
    nsi_results_df
    return


@app.cell
def _(mo, nsi_results_df):
    file_path = "tests/data/nsi_results.csv"
    nsi_results_df.write_csv(file_path)
    mo.md(f"Dataframe saved to `{file_path}`.")
    return


if __name__ == "__main__":
    app.run()
