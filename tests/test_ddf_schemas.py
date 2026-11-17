"""Schema and enum checks for every row of the shipped damage-function CSVs.

The CSVs are a pinned fork of fema-ffrd/inland-consequences (see THIRD_PARTY_NOTICES.md)
and are not edited here. Known problems in that data are pinned below as exact sets:
a new problem fails the test, and so does a fix that does not update the pin.
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

STRUCTURE = "damage_curves_structure.csv"
CONTENTS = "damage_curves_contents.csv"

# --- Known issues in the forked data (Inland commit d713a48), pinned on purpose ---
KNOWN_BLANK_ROWS = {STRUCTURE: 52}  # trailing all-comma rows
KNOWN_DUPLICATE_IDS = {
    STRUCTURE: {*range(550, 597), 700, 701, 702, 703, 704, 705, 707, 708, 710,
                711, 712, 713, 714, 715, 716, 718, 719, 720, 721},
    CONTENTS: {407, 554, 555, 556, 560, 562, 563, 579, 580, 581, 585, 588},
}
KNOWN_OVER_100_PERCENT = {STRUCTURE: {928, 931, 932, 933, 934, 935}}
# 1283-1286 are used by basement lookups: 7% at -4..-2 ft, then 0% until +2 ft.
KNOWN_DECREASING = {STRUCTURE: {160, 271, 1283, 1284, 1285, 1286, *range(1311, 1319)}}


def _read(filename: str) -> pd.DataFrame:
    with resources.files("sphere.data").joinpath(filename).open("r", encoding="utf-8-sig") as f:
        return pd.read_csv(f, dtype=str)


def _non_blank(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.notna().any(axis=1)]


def _depth_values(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["DDF_ID", "Originator Source"]).astype(float)


def _ids(df: pd.DataFrame, mask) -> set[int]:
    return set(df.loc[mask, "DDF_ID"].astype(int))


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
    curves = _non_blank(_read(LOOKUP_CURVES[lookup]))
    missing = set(_read(lookup)["damage_function_id"].astype(int)) - set(curves["DDF_ID"].astype(int))
    assert missing == set()


@pytest.mark.parametrize("lookup", LOOKUP_CURVES)
def test_lookup_ids_never_point_at_ambiguous_or_out_of_range_curves(lookup):
    curve_file = LOOKUP_CURVES[lookup]
    bad = KNOWN_DUPLICATE_IDS.get(curve_file, set()) | KNOWN_OVER_100_PERCENT.get(curve_file, set())
    assert set(_read(lookup)["damage_function_id"].astype(int)) & bad == set()


# ------------------------------------------------------------------------------ curves


@pytest.mark.parametrize("filename", CURVE_SCHEMAS)
def test_curve_rows_match_schema(filename):
    df = _non_blank(_read(filename))
    pinned = df["DDF_ID"].astype(int).isin(KNOWN_OVER_100_PERCENT.get(filename, set()))
    assert _schema_errors(df[~pinned], CURVE_SCHEMAS[filename]) == []


@pytest.mark.parametrize("filename", CURVE_SCHEMAS)
def test_curve_blank_rows_are_pinned(filename):
    df = _read(filename)
    assert len(df) - len(_non_blank(df)) == KNOWN_BLANK_ROWS.get(filename, 0)


@pytest.mark.parametrize("filename", CURVE_SCHEMAS)
def test_curve_duplicate_ids_are_pinned(filename):
    df = _non_blank(_read(filename))
    assert _ids(df, df["DDF_ID"].duplicated(keep=False)) == KNOWN_DUPLICATE_IDS.get(filename, set())


@pytest.mark.parametrize("filename", CURVE_SCHEMAS)
def test_curves_over_100_percent_are_pinned(filename):
    df = _non_blank(_read(filename))
    assert _ids(df, (_depth_values(df) > 100).any(axis=1)) == KNOWN_OVER_100_PERCENT.get(filename, set())


@pytest.mark.parametrize("filename", CURVE_SCHEMAS)
def test_curves_that_decrease_with_depth_are_pinned(filename):
    df = _non_blank(_read(filename))
    decreasing = (_depth_values(df).diff(axis=1) < 0).any(axis=1)
    assert _ids(df, decreasing) == KNOWN_DECREASING.get(filename, set())


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
