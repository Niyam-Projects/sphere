"""Schemas for the damage-function (DDF) CSVs used by ``HazusFloodAnalysis2``.

Lookups map building attributes to a ``damage_function_id``:
``df_lookup_structures.csv``, ``df_lookup_contents.csv``, ``df_lookup_inventory.csv``.
Curves give percent damage by flood depth for each ``DDF_ID``:
``damage_curves_structure.csv``, ``damage_curves_contents.csv``, ``damage_curves_inventory.csv``.

``tests/test_ddf_schemas.py`` checks every shipped row against these definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ConstructionType(str, Enum):
    C = "C"
    H = "H"
    M = "M"
    MH = "MH"
    S = "S"
    W = "W"


class Occupancy(str, Enum):
    AGR1 = "AGR1"
    COM1 = "COM1"
    COM2 = "COM2"
    COM3 = "COM3"
    COM4 = "COM4"
    COM5 = "COM5"
    COM6 = "COM6"
    COM7 = "COM7"
    COM8 = "COM8"
    COM9 = "COM9"
    COM10 = "COM10"
    EDU1 = "EDU1"
    EDU2 = "EDU2"
    GOV1 = "GOV1"
    GOV2 = "GOV2"
    IND1 = "IND1"
    IND2 = "IND2"
    IND3 = "IND3"
    IND4 = "IND4"
    IND5 = "IND5"
    IND6 = "IND6"
    REL1 = "REL1"
    RES1 = "RES1"
    RES2 = "RES2"
    RES3A = "RES3A"
    RES3B = "RES3B"
    RES3C = "RES3C"
    RES3D = "RES3D"
    RES3E = "RES3E"
    RES3F = "RES3F"
    RES4 = "RES4"
    RES5 = "RES5"
    RES6 = "RES6"


class FoundationType(str, Enum):
    BASEMENT = "BASEMENT"
    PILE = "PILE"
    SHALLOW = "SHALLOW"
    SLAB = "SLAB"


class FloodPeril(str, Enum):
    """Riverine: R + velocity (L/H) + duration (S/L). Coastal: CST, CMV, CHW by depth."""

    RLS = "RLS"
    RLL = "RLL"
    RHS = "RHS"
    RHL = "RHL"
    CST = "CST"
    CMV = "CMV"
    CHW = "CHW"


class Duration(str, Enum):
    SHORT = "Short Duration"
    LONG = "Long Duration"


class BaseType(str, Enum):
    BASE = "BASE"
    NOBASE = "NOBASE"


# Contents lookup columns that are derived from other columns.
PERIL_DURATION = {FloodPeril.RLL: Duration.LONG, FloodPeril.RHL: Duration.LONG}  # others: SHORT
FOUNDATION_BASE_TYPE = {FoundationType.BASEMENT: BaseType.BASE}  # every other foundation is NOBASE


@dataclass(frozen=True)
class Column:
    """One CSV column. ``kind`` is ``int``, ``float``, ``str`` or an Enum class."""

    name: str
    kind: type
    nullable: bool = False
    min: float | None = None
    max: float | None = None


_LOOKUP_KEY = (
    Column("construction_type", ConstructionType),
    Column("occupancy_type", Occupancy),
)
_PERIL_AND_ID = (
    Column("foundation_type", FoundationType),
    Column("flood_peril_type", FloodPeril),
    Column("damage_function_id", int, min=1),
)

LOOKUP_SCHEMAS: dict[str, tuple[Column, ...]] = {
    "df_lookup_structures.csv": (
        *_LOOKUP_KEY,
        Column("story_min", int, min=1),
        Column("story_max", int, min=1),
        Column("sqft_min", int, nullable=True, min=0),
        Column("sqft_max", int, nullable=True, min=0),
        *_PERIL_AND_ID,
    ),
    "df_lookup_contents.csv": (
        *_LOOKUP_KEY,
        Column("story_min", int, nullable=True, min=1),
        Column("story_max", int, nullable=True, min=1),
        Column("sqft_min", int, nullable=True, min=0),
        Column("sqft_max", int, nullable=True, min=0),
        *_PERIL_AND_ID,
        Column("Duration", Duration),
        Column("Base Type", BaseType),
    ),
    "df_lookup_inventory.csv": (
        Column("occupancy_type", Occupancy),
        *_PERIL_AND_ID,
    ),
}


def _depth_column_name(depth_ft: float) -> str:
    """-12 -> ft12m, -1.5 -> ft1_5m, 0 -> ft00, 0.5 -> ft0_5, 24 -> ft24."""
    magnitude = abs(depth_ft)
    text = f"{int(magnitude):02d}" if magnitude == int(magnitude) else f"{magnitude:g}".replace(".", "_")
    return f"ft{text}{'m' if depth_ft < 0 else ''}"


def depth_columns(min_depth_ft: int, max_depth_ft: int = 24) -> tuple[tuple[str, float], ...]:
    """Depth columns in file order: whole feet, plus half feet between -2 and +2."""
    half_steps = [-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    depths = [*range(min_depth_ft, -1), *half_steps, *range(2, max_depth_ft + 1)]
    return tuple((_depth_column_name(d), float(d)) for d in depths)


def curve_schema(min_depth_ft: int) -> tuple[Column, ...]:
    return (
        Column("DDF_ID", int, min=1),
        Column("Originator Source", str),
        *(Column(name, float, min=0, max=100) for name, _ in depth_columns(min_depth_ft)),
    )


CURVE_SCHEMAS: dict[str, tuple[Column, ...]] = {
    "damage_curves_structure.csv": curve_schema(-12),
    "damage_curves_contents.csv": curve_schema(-12),
    "damage_curves_inventory.csv": curve_schema(-8),
}

# Which curve table each lookup's damage_function_id points into.
LOOKUP_CURVES = {
    "df_lookup_structures.csv": "damage_curves_structure.csv",
    "df_lookup_contents.csv": "damage_curves_contents.csv",
    "df_lookup_inventory.csv": "damage_curves_inventory.csv",
}
