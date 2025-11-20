import dataclasses
from dataclasses import dataclass
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from sphere.tsunami.analysis.hazus_tsunami import HazusTsunamiAnalysis


@dataclass
class BuildingTestCase:
    id: str
    inputs: dict
    expected_losses: dict


class Fields:
    area = "Area"
    building_cost = "BldgCost"
    content_cost = "CntCost"
    first_floor_height = "FirstFloor"
    flood_depth = "FloodDepth"
    flux = "Flux"
    probability_str_moderate = "PModStr"
    probability_str_extensive = "PExtStr"
    probability_str_complete = "PCompStr"
    probability_nsd_moderate = "PModNsd"
    probability_nsd_extensive = "PExtNsd"
    probability_nsd_complete = "PCompNsd"
    probability_nsd_none = "PNoneNsd"
    probability_content_moderate = "PModCnt"
    probability_content_extensive = "PExtCnt"
    probability_content_complete = "PCompCnt"
    probability_content_none = "PNoneCnt"
    building_loss = "BldgLossUSD"
    content_loss = "CntLossUSD"
    relocation_loss = "RelocLossUSD"
    income_loss = "IncLossUSD"
    rental_loss = "RentLossUSD"
    wage_loss = "WageLossUSD"
    occupancy_type = "Occupancy"


class BuildingsObj:
    def __init__(self, gdf, fields):
        self.gdf = gdf
        self.fields = fields()


class MockRasterReader:
    def __init__(self, val):
        self.val = val

    def get_value_vectorized(self, geometries):
        return np.full(len(geometries), self.val, dtype=float)


class DamageRatioVulnerability:
    """Vulnerability that sets probabilities from an input damage_ratio per-row.

    If the test provides explicit probability columns in inputs those are used; otherwise
    `damage_ratio` is interpreted as the probability of complete structural damage and
    is copied to non-structural and contents complete probabilities as a simple default.
    """

    def compute_damage_states(self, buildings):
        gdf = buildings.gdf
        f = buildings.fields

        # if caller provided explicit probability columns, leave them
        if f.probability_str_complete in gdf.columns and not gdf[f.probability_str_complete].isnull().all():
            # assume tests provided probabilities explicitly
            return

        # otherwise read damage_ratio and set probabilities
        if "damage_ratio" in gdf.columns:
            dr = gdf["damage_ratio"].fillna(0.0)
        else:
            dr = pd.Series(np.zeros(len(gdf)), index=gdf.index)

        gdf[f.probability_str_complete] = dr
        gdf[f.probability_str_extensive] = 0.0
        gdf[f.probability_str_moderate] = 0.0

        # non-structural and contents default to same complete ratio (tests can override)
        gdf[f.probability_nsd_complete] = dr
        gdf[f.probability_nsd_extensive] = 0.0
        gdf[f.probability_nsd_moderate] = 0.0

        gdf[f.probability_content_complete] = dr
        gdf[f.probability_content_extensive] = 0.0
        gdf[f.probability_content_moderate] = 0.0


def make_gdf_from_inputs(inputs: dict, fields: Fields) -> gpd.GeoDataFrame:
    # map user-friendly input keys to the field names expected by the analysis
    bcost = inputs.get("replacement_cost", inputs.get("building_cost", 0.0))
    cnt = inputs.get("content_cost", inputs.get("content_cost", 0.0))
    area = inputs.get("area", 100.0)
    first_floor = inputs.get("first_floor_height", 0.0)
    occ = inputs.get("occupancy", "RES")

    geom = [Point(0, 0)]

    row = {
        fields.area: [area],
        fields.building_cost: [bcost],
        fields.content_cost: [cnt],
        fields.first_floor_height: [first_floor],
        fields.occupancy_type: [occ],
    }

    # include damage_ratio if present (used by DamageRatioVulnerability)
    if "damage_ratio" in inputs:
        row["damage_ratio"] = [inputs["damage_ratio"]]

    # include any explicit probability columns if test provided them
    for col in [
        fields.probability_str_complete,
        fields.probability_str_extensive,
        fields.probability_str_moderate,
        fields.probability_nsd_complete,
        fields.probability_nsd_extensive,
        fields.probability_nsd_moderate,
        fields.probability_content_complete,
        fields.probability_content_extensive,
        fields.probability_content_moderate,
    ]:
        if col in inputs:
            row[col] = [inputs[col]]

    gdf = gpd.GeoDataFrame(row, geometry=geom, crs="EPSG:4326")
    return gdf


def test_building_test_cases_loop():
    f = Fields()

    # define test cases; user-provided example plus couple more
    cases = [
        BuildingTestCase(
            id="BLD_001",
            inputs={
                "building_id": "BLD_001",
                "replacement_cost": 100_000.0,
                "content_cost": 50_000.0,
                "damage_ratio": 1.0,
            },
            expected_losses={
                "structureLossUSD": 100_000.0,
                "contentLossUSD": 50_000.0,
                "totalLossUSD": 150_000.0,
            },
        ),
        BuildingTestCase(
            id="BLD_002",
            inputs={
                "building_id": "BLD_002",
                "replacement_cost": 200_000.0,
                "content_cost": 80_000.0,
                "damage_ratio": 0.5,
            },
            expected_losses={
                "structureLossUSD": 100_000.0,  # 200k * 0.5
                "contentLossUSD": 40_000.0,     # 80k * 0.5
                "totalLossUSD": 140_000.0,
            },
        ),
        BuildingTestCase(
            id="BLD_003",
            inputs={
                "building_id": "BLD_003",
                "replacement_cost": 50_000.0,
                "content_cost": 10_000.0,
                "damage_ratio": 0.0,
            },
            expected_losses={
                "structureLossUSD": 0.0,
                "contentLossUSD": 0.0,
                "totalLossUSD": 0.0,
            },
        ),
    ]

    for case in cases:
        gdf = make_gdf_from_inputs(case.inputs, Fields)
        buildings = BuildingsObj(gdf, Fields)

        # mocks
        depth_mock = MockRasterReader(0.0)
        flux_mock = MockRasterReader(0.0)
        vuln = DamageRatioVulnerability()

        analysis = HazusTsunamiAnalysis(buildings, vuln, depth_mock, flux_mock)

        # inject deterministic economic params so that CmpStrRepair = 100 and CmpCntRepair = 100
        # and non-structural repairs are zero so losses = damage_ratio * replacement/content
        analysis.economic_params = pd.DataFrame([{
            "Occupancy": "RES",
            "ModStrRepair": 0.0, "ExtStrRepair": 0.0, "CmpStrRepair": 100.0,
            "ModNsaRepair": 0.0, "ModNsdRepair": 0.0, "ExtNsaRepair": 0.0, "ExtNsdRepair": 0.0,
            "CmpNsaRepair": 0.0, "CmpNsdRepair": 0.0,
            "ModCntRepair": 0.0, "ExtCntRepair": 0.0, "CmpCntRepair": 100.0,
            "DisruptCostPerMonth": 0.0, "RentPerDay": 0.0, "ModRecoveryTime": 0.0, "ExtRecoveryTime": 0.0, "CmpRecoveryTime": 0.0,
            "IncPerDay": 0.0, "ModConstrTime": 0.0, "ExtConstrTime": 0.0, "CmpConstrTime": 0.0,
            "PctOwnerOcc": 100.0, "IncomeRecap": 1.0, "WageRecap": 1.0, "WagePerDay": 0.0
        }])

        out = analysis.calculate_losses()

        # single-row result
        row = out.iloc[0]

        # compute actual values for comparison
        actual_struct = float(row["StructLoss"])
        actual_content = float(row[f.content_loss])
        actual_total = actual_struct + actual_content

        assert np.isclose(actual_struct, case.expected_losses["structureLossUSD"], rtol=1e-6), (
            f"Struct mismatch for {case.id}: got {actual_struct}, expected {case.expected_losses['structureLossUSD']}"
        )
        assert np.isclose(actual_content, case.expected_losses["contentLossUSD"], rtol=1e-6), (
            f"Content mismatch for {case.id}: got {actual_content}, expected {case.expected_losses['contentLossUSD']}"
        )
        assert np.isclose(actual_total, case.expected_losses["totalLossUSD"], rtol=1e-6), (
            f"Total mismatch for {case.id}: got {actual_total}, expected {case.expected_losses['totalLossUSD']}"
        )
