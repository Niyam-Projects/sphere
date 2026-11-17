"""Schema and enum checks for the damage-function lookup and curve CSVs.

Every lookup row is checked against its schema, and every curve a lookup uses
is checked against the curve schema.
"""
from __future__ import annotations

import itertools
from enum import Enum
from importlib import resources

import pandas as pd
import pytest

from sphere.data.ddf_schema import (
    CURVE_SCHEMAS,
    FOUNDATION_BASE_TYPE,
    LOOKUP_CURVES,
    LOOKUP_SCHEMAS,
    PERIL_DURATION,
    BaseType,
    Column,
    Duration,
    FloodPeril,
    FoundationType,
    Occupancy,
)


def _read(filename: str) -> pd.DataFrame:
    with resources.files("sphere.data").joinpath(filename).open("r", encoding="utf-8-sig") as f:
        return pd.read_csv(f, dtype=str)


def _schema_errors(df: pd.DataFrame, columns: tuple[Column, ...]) -> list[str]:
    """Every way ``df`` breaks ``columns``: order, nulls, enums, types and ranges."""
    expected = [c.name for c in columns]
    if list(df.columns) != expected:
        return [f"columns {list(df.columns)} != {expected}"]
    errors = []
    for col in columns:
        values = df[col.name]
        if not col.nullable and values.isna().any():
            errors.append(f"{col.name}: {int(values.isna().sum())} empty values")
        present = values.dropna()
        if isinstance(col.kind, type) and issubclass(col.kind, Enum):
            unknown = set(present) - {m.value for m in col.kind}
            if unknown:
                errors.append(f"{col.name}: not in {col.kind.__name__}: {sorted(unknown)}")
            continue
        if col.kind is str:
            continue
        numbers = pd.to_numeric(present, errors="coerce")
        if numbers.isna().any():
            errors.append(f"{col.name}: not numeric: {sorted(set(present[numbers.isna()]))[:5]}")
        numbers = numbers.dropna()
        if col.kind is int and (numbers % 1 != 0).any():
            errors.append(f"{col.name}: not whole numbers: {sorted(set(numbers[numbers % 1 != 0]))[:5]}")
        if col.min is not None and (numbers < col.min).any():
            errors.append(f"{col.name}: below {col.min}: {sorted(set(numbers[numbers < col.min]))[:5]}")
        if col.max is not None and (numbers > col.max).any():
            errors.append(f"{col.name}: above {col.max}: {sorted(set(numbers[numbers > col.max]))[:5]}")
    return errors


# ----------------------------------------------------------------------------- lookups


@pytest.mark.parametrize("filename", LOOKUP_SCHEMAS)
def test_lookup_matches_schema(filename):
    assert _schema_errors(_read(filename), LOOKUP_SCHEMAS[filename]) == []


@pytest.mark.parametrize("filename", LOOKUP_SCHEMAS)
def test_lookup_has_no_duplicate_rows(filename):
    df = _read(filename)
    assert df[df.duplicated(keep=False)].empty


@pytest.mark.parametrize("filename", ["df_lookup_structures.csv", "df_lookup_contents.csv"])
def test_lookup_ranges_are_ordered_and_paired(filename):
    df = _read(filename)
    for low, high in [("story_min", "story_max"), ("sqft_min", "sqft_max")]:
        both = df[[low, high]].dropna().astype(int)
        assert (both[low] <= both[high]).all(), f"{low} > {high}"
    # story bounds come as a pair; sqft may be open-ended (e.g. 4001 and up)
    assert (df["story_min"].isna() == df["story_max"].isna()).all()


def test_contents_duration_and_base_type_follow_peril_and_foundation():
    df = _read("df_lookup_contents.csv")
    duration = df["flood_peril_type"].map(lambda p: PERIL_DURATION.get(FloodPeril(p), Duration.SHORT).value)
    base_type = df["foundation_type"].map(
        lambda f: FOUNDATION_BASE_TYPE.get(FoundationType(f), BaseType.NOBASE).value
    )
    assert (df["Duration"] == duration).all()
    assert (df["Base Type"] == base_type).all()


@pytest.mark.parametrize("filename", LOOKUP_SCHEMAS)
def test_every_occupancy_foundation_peril_has_a_curve(filename):
    """A combination with no row means buildings silently get no loss (issue #15)."""
    df = _read(filename)
    occupancies = list(Occupancy) if filename != "df_lookup_inventory.csv" else [
        Occupancy(o) for o in sorted(set(df["occupancy_type"]))  # inventory is only defined for some
    ]
    expected = {
        (o.value, f.value, p.value)
        for o, f, p in itertools.product(occupancies, FoundationType, FloodPeril)
    }
    present = set(df[["occupancy_type", "foundation_type", "flood_peril_type"]].itertuples(index=False, name=None))
    assert expected - present == set()


@pytest.mark.parametrize("lookup", LOOKUP_CURVES)
def test_lookup_ids_exist_in_curve_table(lookup):
    missing = set(_read(lookup)["damage_function_id"]) - set(_read(LOOKUP_CURVES[lookup])["DDF_ID"])
    assert missing == set()


# ------------------------------------------------------------------------------ curves


def _used_curves(curve_file: str) -> pd.DataFrame:
    used_ids = set()
    for lookup, target in LOOKUP_CURVES.items():
        if target == curve_file:
            used_ids |= set(_read(lookup)["damage_function_id"])
    curves = _read(curve_file)
    return curves[curves["DDF_ID"].isin(used_ids)]


@pytest.mark.parametrize("filename", CURVE_SCHEMAS)
def test_used_curves_match_schema(filename):
    assert _schema_errors(_used_curves(filename), CURVE_SCHEMAS[filename]) == []


# ------------------------------------------------------------------- the checker itself


def test_schema_errors_reports_each_kind_of_problem():
    columns = (
        Column("occupancy_type", Occupancy),
        Column("story_min", int, min=1),
        Column("pct", float, min=0, max=100),
    )
    df = pd.DataFrame({"occupancy_type": ["RES1", "RES9"], "story_min": ["0", "1.5"], "pct": [None, "101"]})

    errors = _schema_errors(df, columns)

    assert errors == [
        "occupancy_type: not in Occupancy: ['RES9']",
        "story_min: not whole numbers: [1.5]",
        "story_min: below 1: [0.0]",
        "pct: 1 empty values",
        "pct: above 100: [101]",
    ]
    assert _schema_errors(df[["pct"]], columns) == [
        f"columns ['pct'] != {[c.name for c in columns]}"
    ]
