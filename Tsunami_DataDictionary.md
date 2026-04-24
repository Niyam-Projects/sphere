# Data Dictionary

## INVENTORY

| FIELD | DESCRIPTION |
|:---|:---|
| ID | Unique National Structure Inventory ID, Milliman and other unique IDs may be used |
| EqBldgType | Earthquake-specific building type classification ID |
| EqDesignLe | Earthquake design level classification ID |
| SOccupID | Hazus specific occupancy type ID |
| Occupancy_Type | Hazus occupancy classification (i.e., RES1, COM1, IND2) |
| FirstFloor | First floor height above ground elevation (feet) |
| ValStruct | Building structure replacement cost (USD) |
| ValCont | Contents replacement cost (USD) |
| AreaSqft | Building floor area (square feet) |
| CBFips | Census Block ID |
| geometry | Locational geometry is required for spatial analysis. |
| Longitude | Site longitude (x) in decimal degrees |
| Latitude | Site latitude (y) in decimal degrees |

## HAZARD

> **Note on MomFlux column names**: The `_ft_per_sec` suffix in `MomFlux_*` column names is a naming
> inconsistency inherited from the TTF tool. The physical units of momentum flux are ft<sup>3</sup>/s<sup>2</sup>
> (cubic feet per second squared), not ft/s. The descriptions in the table below reflect the
> correct units.

| FIELD | DESCRIPTION |
|:---|:---|
| Point | Unique point ID provided by TTF tool |
| FlowDepth_10yr_Median_ft | Median flow depth in feet for the 10-year return period |
| FlowDepth_25yr_Median_ft | Median flow depth in feet for the 25-year return period |
| FlowDepth_50yr_Median_ft | Median flow depth in feet for the 50-year return period |
| FlowDepth_72yr_Median_ft | Median flow depth in feet for the 72-year return period |
| FlowDepth_100yr_Median_ft | Median flow depth in feet for the 100-year return period |
| FlowDepth_150yr_Median_ft | Median flow depth in feet for the 150-year return period |
| FlowDepth_200yr_Median_ft | Median flow depth in feet for the 200-year return period |
| FlowDepth_250yr_Median_ft | Median flow depth in feet for the 250-year return period |
| FlowDepth_475yr_Median_ft | Median flow depth in feet for the 475-year return period |
| FlowDepth_750yr_Median_ft | Median flow depth in feet for the 750-year return period |
| FlowDepth_975yr_Median_ft | Median flow depth in feet for the 975-year return period |
| FlowDepth_1500yr_Median_ft | Median flow depth in feet for the 1500-year return period |
| FlowDepth_2475yr_Median_ft | Median flow depth in feet for the 2475-year return period |
| FlowDepth_3000yr_Median_ft | Median flow depth in feet for the 3000-year return period |
| Speed_10yr_Median_ft_per_sec | Median velocity in feet per second for the 10-year return period |
| Speed_25yr_Median_ft_per_sec | Median velocity in feet per second for the 25-year return period |
| Speed_50yr_Median_ft_per_sec | Median velocity in feet per second for the 50-year return period |
| Speed_72yr_Median_ft_per_sec | Median velocity in feet per second for the 72-year return period |
| Speed_100yr_Median_ft_per_sec | Median velocity in feet per second for the 100-year return period |
| Speed_150yr_Median_ft_per_sec | Median velocity in feet per second for the 150-year return period |
| Speed_200yr_Median_ft_per_sec | Median velocity in feet per second for the 200-year return period |
| Speed_250yr_Median_ft_per_sec | Median velocity in feet per second for the 250-year return period |
| Speed_475yr_Median_ft_per_sec | Median velocity in feet per second for the 475-year return period |
| Speed_750yr_Median_ft_per_sec | Median velocity in feet per second for the 750-year return period |
| Speed_975yr_Median_ft_per_sec | Median velocity in feet per second for the 975-year return period |
| Speed_1500yr_Median_ft_per_sec | Median velocity in feet per second for the 1500-year return period |
| Speed_2475yr_Median_ft_per_sec | Median velocity in feet per second for the 2475-year return period |
| Speed_3000yr_Median_ft_per_sec | Median velocity in feet per second for the 3000-year return period |
| MomFlux_10yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 10-year return period |
| MomFlux_25yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 25-year return period |
| MomFlux_50yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 50-year return period |
| MomFlux_72yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 72-year return period |
| MomFlux_100yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 100-year return period |
| MomFlux_150yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 150-year return period |
| MomFlux_200yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 200-year return period |
| MomFlux_250yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 250-year return period |
| MomFlux_475yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 475-year return period |
| MomFlux_750yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 750-year return period |
| MomFlux_975yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 975-year return period |
| MomFlux_1500yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 1500-year return period |
| MomFlux_2475yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 2475-year return period |
| MomFlux_3000yr_Median_ft_per_sec | Median momentum flux in cubic feet per second squared for the 3000-year return period |
| First_Wet_RP_yrs | First return period in years where flow depth is > 0 |
| Site_Elevation_ft | Ground elevation at the site |
| Grid_Index | TTF grid index referencing the source grid for the anchor data |
| AnchorPt_Index | TTF index number referring to if the 975 year (1) or 2475 (2) is used to provide the flow depth return period anchor |
| depth_in_structure_10y | Flow depth in structure in feet (median flow depth minus foundation height) for the 10-year return period |
| depth_in_structure_25y | Flow depth in structure in feet (median flow depth minus foundation height) for the 25-year return period |
| depth_in_structure_50y | Flow depth in structure in feet (median flow depth minus foundation height) for the 50-year return period |
| depth_in_structure_72y | Flow depth in structure in feet (median flow depth minus foundation height) for the 72-year return period |
| depth_in_structure_100y | Flow depth in structure in feet (median flow depth minus foundation height) for the 100-year return period |
| depth_in_structure_150y | Flow depth in structure in feet (median flow depth minus foundation height) for the 150-year return period |
| depth_in_structure_200y | Flow depth in structure in feet (median flow depth minus foundation height) for the 200-year return period |
| depth_in_structure_250y | Flow depth in structure in feet (median flow depth minus foundation height) for the 250-year return period |
| depth_in_structure_475y | Flow depth in structure in feet (median flow depth minus foundation height) for the 475-year return period |
| depth_in_structure_750y | Flow depth in structure in feet (median flow depth minus foundation height) for the 750-year return period |
| depth_in_structure_975y | Flow depth in structure in feet (median flow depth minus foundation height) for the 975-year return period |
| depth_in_structure_1500y | Flow depth in structure in feet (median flow depth minus foundation height) for the 1500-year return period |
| depth_in_structure_2475y | Flow depth in structure in feet (median flow depth minus foundation height) for the 2475-year return period |
| depth_in_structure_3000y | Flow depth in structure in feet (median flow depth minus foundation height) for the 3000-year return period |

## DAMAGE STATE PROBABILITIES

| FIELD | DESCRIPTION |
|:---|:---|
| p_str_comp_10y | Probability of structural complete damage state for the 10-year return period |
| p_str_comp_25y | Probability of structural complete damage state for the 25-year return period |
| p_str_comp_50y | Probability of structural complete damage state for the 50-year return period |
| p_str_comp_72y | Probability of structural complete damage state for the 72-year return period |
| p_str_comp_100y | Probability of structural complete damage state for the 100-year return period |
| p_str_comp_150y | Probability of structural complete damage state for the 150-year return period |
| p_str_comp_200y | Probability of structural complete damage state for the 200-year return period |
| p_str_comp_250y | Probability of structural complete damage state for the 250-year return period |
| p_str_comp_475y | Probability of structural complete damage state for the 475-year return period |
| p_str_comp_750y | Probability of structural complete damage state for the 750-year return period |
| p_str_comp_975y | Probability of structural complete damage state for the 975-year return period |
| p_str_comp_1500y | Probability of structural complete damage state for the 1500-year return period |
| p_str_comp_2475y | Probability of structural complete damage state for the 2475-year return period |
| p_str_comp_3000y | Probability of structural complete damage state for the 3000-year return period |
| p_str_ext_10y | Probability of structural extensive damage state for the 10-year return period |
| p_str_ext_25y | Probability of structural extensive damage state for the 25-year return period |
| p_str_ext_50y | Probability of structural extensive damage state for the 50-year return period |
| p_str_ext_72y | Probability of structural extensive damage state for the 72-year return period |
| p_str_ext_100y | Probability of structural extensive damage state for the 100-year return period |
| p_str_ext_150y | Probability of structural extensive damage state for the 150-year return period |
| p_str_ext_200y | Probability of structural extensive damage state for the 200-year return period |
| p_str_ext_250y | Probability of structural extensive damage state for the 250-year return period |
| p_str_ext_475y | Probability of structural extensive damage state for the 475-year return period |
| p_str_ext_750y | Probability of structural extensive damage state for the 750-year return period |
| p_str_ext_975y | Probability of structural extensive damage state for the 975-year return period |
| p_str_ext_1500y | Probability of structural extensive damage state for the 1500-year return period |
| p_str_ext_2475y | Probability of structural extensive damage state for the 2475-year return period |
| p_str_ext_3000y | Probability of structural extensive damage state for the 3000-year return period |
| p_str_mod_10y | Probability of structural moderate damage state for the 10-year return period |
| p_str_mod_25y | Probability of structural moderate damage state for the 25-year return period |
| p_str_mod_50y | Probability of structural moderate damage state for the 50-year return period |
| p_str_mod_72y | Probability of structural moderate damage state for the 72-year return period |
| p_str_mod_100y | Probability of structural moderate damage state for the 100-year return period |
| p_str_mod_150y | Probability of structural moderate damage state for the 150-year return period |
| p_str_mod_200y | Probability of structural moderate damage state for the 200-year return period |
| p_str_mod_250y | Probability of structural moderate damage state for the 250-year return period |
| p_str_mod_475y | Probability of structural moderate damage state for the 475-year return period |
| p_str_mod_750y | Probability of structural moderate damage state for the 750-year return period |
| p_str_mod_975y | Probability of structural moderate damage state for the 975-year return period |
| p_str_mod_1500y | Probability of structural moderate damage state for the 1500-year return period |
| p_str_mod_2475y | Probability of structural moderate damage state for the 2475-year return period |
| p_str_mod_3000y | Probability of structural moderate damage state for the 3000-year return period |
| p_str_none_10y | Probability of structural none damage state for the 10-year return period |
| p_str_none_25y | Probability of structural none damage state for the 25-year return period |
| p_str_none_50y | Probability of structural none damage state for the 50-year return period |
| p_str_none_72y | Probability of structural none damage state for the 72-year return period |
| p_str_none_100y | Probability of structural none damage state for the 100-year return period |
| p_str_none_150y | Probability of structural none damage state for the 150-year return period |
| p_str_none_200y | Probability of structural none damage state for the 200-year return period |
| p_str_none_250y | Probability of structural none damage state for the 250-year return period |
| p_str_none_475y | Probability of structural none damage state for the 475-year return period |
| p_str_none_750y | Probability of structural none damage state for the 750-year return period |
| p_str_none_975y | Probability of structural none damage state for the 975-year return period |
| p_str_none_1500y | Probability of structural none damage state for the 1500-year return period |
| p_str_none_2475y | Probability of structural none damage state for the 2475-year return period |
| p_str_none_3000y | Probability of structural none damage state for the 3000-year return period |
| p_nsd_comp_10y | Probability of non structural complete damage state for the 10-year return period |
| p_nsd_comp_25y | Probability of non structural complete damage state for the 25-year return period |
| p_nsd_comp_50y | Probability of non structural complete damage state for the 50-year return period |
| p_nsd_comp_72y | Probability of non structural complete damage state for the 72-year return period |
| p_nsd_comp_100y | Probability of non structural complete damage state for the 100-year return period |
| p_nsd_comp_150y | Probability of non structural complete damage state for the 150-year return period |
| p_nsd_comp_200y | Probability of non structural complete damage state for the 200-year return period |
| p_nsd_comp_250y | Probability of non structural complete damage state for the 250-year return period |
| p_nsd_comp_475y | Probability of non structural complete damage state for the 475-year return period |
| p_nsd_comp_750y | Probability of non structural complete damage state for the 750-year return period |
| p_nsd_comp_975y | Probability of non structural complete damage state for the 975-year return period |
| p_nsd_comp_1500y | Probability of non structural complete damage state for the 1500-year return period |
| p_nsd_comp_2475y | Probability of non structural complete damage state for the 2475-year return period |
| p_nsd_comp_3000y | Probability of non structural complete damage state for the 3000-year return period |
| p_nsd_ext_10y | Probability of non structural extensive damage state for the 10-year return period |
| p_nsd_ext_25y | Probability of non structural extensive damage state for the 25-year return period |
| p_nsd_ext_50y | Probability of non structural extensive damage state for the 50-year return period |
| p_nsd_ext_72y | Probability of non structural extensive damage state for the 72-year return period |
| p_nsd_ext_100y | Probability of non structural extensive damage state for the 100-year return period |
| p_nsd_ext_150y | Probability of non structural extensive damage state for the 150-year return period |
| p_nsd_ext_200y | Probability of non structural extensive damage state for the 200-year return period |
| p_nsd_ext_250y | Probability of non structural extensive damage state for the 250-year return period |
| p_nsd_ext_475y | Probability of non structural extensive damage state for the 475-year return period |
| p_nsd_ext_750y | Probability of non structural extensive damage state for the 750-year return period |
| p_nsd_ext_975y | Probability of non structural extensive damage state for the 975-year return period |
| p_nsd_ext_1500y | Probability of non structural extensive damage state for the 1500-year return period |
| p_nsd_ext_2475y | Probability of non structural extensive damage state for the 2475-year return period |
| p_nsd_ext_3000y | Probability of non structural extensive damage state for the 3000-year return period |
| p_nsd_mod_10y | Probability of non structural moderate damage state for the 10-year return period |
| p_nsd_mod_25y | Probability of non structural moderate damage state for the 25-year return period |
| p_nsd_mod_50y | Probability of non structural moderate damage state for the 50-year return period |
| p_nsd_mod_72y | Probability of non structural moderate damage state for the 72-year return period |
| p_nsd_mod_100y | Probability of non structural moderate damage state for the 100-year return period |
| p_nsd_mod_150y | Probability of non structural moderate damage state for the 150-year return period |
| p_nsd_mod_200y | Probability of non structural moderate damage state for the 200-year return period |
| p_nsd_mod_250y | Probability of non structural moderate damage state for the 250-year return period |
| p_nsd_mod_475y | Probability of non structural moderate damage state for the 475-year return period |
| p_nsd_mod_750y | Probability of non structural moderate damage state for the 750-year return period |
| p_nsd_mod_975y | Probability of non structural moderate damage state for the 975-year return period |
| p_nsd_mod_1500y | Probability of non structural moderate damage state for the 1500-year return period |
| p_nsd_mod_2475y | Probability of non structural moderate damage state for the 2475-year return period |
| p_nsd_mod_3000y | Probability of non structural moderate damage state for the 3000-year return period |
| p_nsd_none_10y | Probability of non structural none damage state for the 10-year return period |
| p_nsd_none_25y | Probability of non structural none damage state for the 25-year return period |
| p_nsd_none_50y | Probability of non structural none damage state for the 50-year return period |
| p_nsd_none_72y | Probability of non structural none damage state for the 72-year return period |
| p_nsd_none_100y | Probability of non structural none damage state for the 100-year return period |
| p_nsd_none_150y | Probability of non structural none damage state for the 150-year return period |
| p_nsd_none_200y | Probability of non structural none damage state for the 200-year return period |
| p_nsd_none_250y | Probability of non structural none damage state for the 250-year return period |
| p_nsd_none_475y | Probability of non structural none damage state for the 475-year return period |
| p_nsd_none_750y | Probability of non structural none damage state for the 750-year return period |
| p_nsd_none_975y | Probability of non structural none damage state for the 975-year return period |
| p_nsd_none_1500y | Probability of non structural none damage state for the 1500-year return period |
| p_nsd_none_2475y | Probability of non structural none damage state for the 2475-year return period |
| p_nsd_none_3000y | Probability of non structural none damage state for the 3000-year return period |
| p_cont_comp_10y | Probability of content complete damage state for the 10-year return period |
| p_cont_comp_25y | Probability of content complete damage state for the 25-year return period |
| p_cont_comp_50y | Probability of content complete damage state for the 50-year return period |
| p_cont_comp_72y | Probability of content complete damage state for the 72-year return period |
| p_cont_comp_100y | Probability of content complete damage state for the 100-year return period |
| p_cont_comp_150y | Probability of content complete damage state for the 150-year return period |
| p_cont_comp_200y | Probability of content complete damage state for the 200-year return period |
| p_cont_comp_250y | Probability of content complete damage state for the 250-year return period |
| p_cont_comp_475y | Probability of content complete damage state for the 475-year return period |
| p_cont_comp_750y | Probability of content complete damage state for the 750-year return period |
| p_cont_comp_975y | Probability of content complete damage state for the 975-year return period |
| p_cont_comp_1500y | Probability of content complete damage state for the 1500-year return period |
| p_cont_comp_2475y | Probability of content complete damage state for the 2475-year return period |
| p_cont_comp_3000y | Probability of content complete damage state for the 3000-year return period |
| p_cont_ext_10y | Probability of content extensive damage state for the 10-year return period |
| p_cont_ext_25y | Probability of content extensive damage state for the 25-year return period |
| p_cont_ext_50y | Probability of content extensive damage state for the 50-year return period |
| p_cont_ext_72y | Probability of content extensive damage state for the 72-year return period |
| p_cont_ext_100y | Probability of content extensive damage state for the 100-year return period |
| p_cont_ext_150y | Probability of content extensive damage state for the 150-year return period |
| p_cont_ext_200y | Probability of content extensive damage state for the 200-year return period |
| p_cont_ext_250y | Probability of content extensive damage state for the 250-year return period |
| p_cont_ext_475y | Probability of content extensive damage state for the 475-year return period |
| p_cont_ext_750y | Probability of content extensive damage state for the 750-year return period |
| p_cont_ext_975y | Probability of content extensive damage state for the 975-year return period |
| p_cont_ext_1500y | Probability of content extensive damage state for the 1500-year return period |
| p_cont_ext_2475y | Probability of content extensive damage state for the 2475-year return period |
| p_cont_ext_3000y | Probability of content extensive damage state for the 3000-year return period |
| p_cont_mod_10y | Probability of content moderate damage state for the 10-year return period |
| p_cont_mod_25y | Probability of content moderate damage state for the 25-year return period |
| p_cont_mod_50y | Probability of content moderate damage state for the 50-year return period |
| p_cont_mod_72y | Probability of content moderate damage state for the 72-year return period |
| p_cont_mod_100y | Probability of content moderate damage state for the 100-year return period |
| p_cont_mod_150y | Probability of content moderate damage state for the 150-year return period |
| p_cont_mod_200y | Probability of content moderate damage state for the 200-year return period |
| p_cont_mod_250y | Probability of content moderate damage state for the 250-year return period |
| p_cont_mod_475y | Probability of content moderate damage state for the 475-year return period |
| p_cont_mod_750y | Probability of content moderate damage state for the 750-year return period |
| p_cont_mod_975y | Probability of content moderate damage state for the 975-year return period |
| p_cont_mod_1500y | Probability of content moderate damage state for the 1500-year return period |
| p_cont_mod_2475y | Probability of content moderate damage state for the 2475-year return period |
| p_cont_mod_3000y | Probability of content moderate damage state for the 3000-year return period |
| p_cont_none_10y | Probability of content none damage state for the 10-year return period |
| p_cont_none_25y | Probability of content none damage state for the 25-year return period |
| p_cont_none_50y | Probability of content none damage state for the 50-year return period |
| p_cont_none_72y | Probability of content none damage state for the 72-year return period |
| p_cont_none_100y | Probability of content none damage state for the 100-year return period |
| p_cont_none_150y | Probability of content none damage state for the 150-year return period |
| p_cont_none_200y | Probability of content none damage state for the 200-year return period |
| p_cont_none_250y | Probability of content none damage state for the 250-year return period |
| p_cont_none_475y | Probability of content none damage state for the 475-year return period |
| p_cont_none_750y | Probability of content none damage state for the 750-year return period |
| p_cont_none_975y | Probability of content none damage state for the 975-year return period |
| p_cont_none_1500y | Probability of content none damage state for the 1500-year return period |
| p_cont_none_2475y | Probability of content none damage state for the 2475-year return period |
| p_cont_none_3000y | Probability of content none damage state for the 3000-year return period |

## ANALYSIS PARAMETERS

| FIELD | DESCRIPTION |
|:---|:---|
| Occupancy | Hazus occupancy classification (i.e., RES1, COM1, IND2) |
| SlightStrRepair | Slight structural damage repair ratio |
| ModStrRepair | Moderate structural damage repair ratio |
| ExtStrRepair | Extensive structural damage repair ratio |
| CmpStrRepair | Complete structural damage repair ratio |
| SlightNsaRepair | Slight non structural acceleration sensitive damage repair ratio |
| ModNsaRepair | Moderate non structural acceleration sensitive damage repair ratio |
| ExtNsaRepair | Extensive non structural acceleration sensitive damage repair ratio |
| CmpNsaRepair | Complete non structural acceleration sensitive damage repair ratio |
| SlightNsdRepair | Slight non structural drift sensitive damage repair ratio |
| ModNsdRepair | Moderate non structural drift sensitive damage repair ratio |
| ExtNsdRepair | Extensive non structural drift sensitive damage repair ratio |
| CmpNsdRepair | Complete non structural drift sensitive damage repair ratio |
| SlightCntRepair | Slight content damage repair ratio |
| ModCntRepair | Moderate content damage repair ratio |
| ExtCntRepair | Extensive content damage repair ratio |
| CmpCntRepair | Complete content damage repair ratio |
| NoneRepairTime | None damage state building repair and cleanup time (days) |
| SlightRepairTime | Slight damage state building repair and cleanup time (days) |
| ModRepairTime | Moderate damage state building repair and cleanup time (days) |
| ExtRepairTime | Extensive damage state building repair and cleanup time (days) |
| CmpRepairTime | Complete damage state building repair and cleanup time (days) |
| NoneRecoveryTime | None damage state recovery time (days) |
| SlightRecoveryTime | Slight damage state recovery time (days) |
| ModRecoveryTime | Moderate damage state recovery time (days) |
| ExtRecoveryTime | Extensive damage state recovery time (days) |
| CmpRecoveryTime | Complete damage state recovery time (days) |
| NoneConstrTime | None damage state construction time modifier (percent of repair time) |
| SlightConstrTime | Slight damage state construction time modifier (percent of repair time) |
| ModConstrTime | Moderate damage state construction time modifier (percent of repair time) |
| ExtConstrTime | Extensive damage state construction time modifier (percent of repair time) |
| CmpConstrTime | Complete damage state construction time modifier (percent of repair time) |
| RentPerDay | Rental costs $ per sq ft per day |
| RentPerMonth | Rental costs $ per sq ft per month |
| DisruptCostPerMonth | Disruption costs $ per sq ft per month |
| PctOwnerOcc | Percent of building occupied by owner |
| IncPerDay | Proprietor income $ per sq ft per day |
| IncPerYear | Proprietor income $ per sq ft per year |
| WagePerDay | Wages paid $ per sq ft per day |
| EmployeePerSqft | Employees per sq ft |
| OutputPerDay | Output $ per sq ft per day |
| WageRecap | Wage recapture factor (percent) |
| EmploymentRecap | Employment recapture factor (percent) |
| IncomeRecap | Income recapture factor (percent) |
| OutputRecap | Output recapture factor (percent) |
| Occupancy_econInc | Hazus occupancy classifications with inventory related losses (i.e., AGR1, COM1-2, IND1-6) |
| GrossSales | Annual gross sales ($ per sq ft) |
| BusinessInv | Business inventory as a percentage of gross annual sales |
| SlightInvDmg | Slight inventory damage repair ratio |
| ModInvDmg | Moderate inventory damage repair ratio |
| ExtInvDmg | Extensive inventory damage repair ratio |
| CmpInvDmg | Complete inventory damage repair ratio |

## LOSSES (RETURN PERIOD)

| FIELD | DESCRIPTION |
|:---|:---|
| StructLoss_10y | Structural building loss ($) for the 10-year return period |
| StructLoss_25y | Structural building loss ($) for the 25-year return period |
| StructLoss_50y | Structural building loss ($) for the 50-year return period |
| StructLoss_72y | Structural building loss ($) for the 72-year return period |
| StructLoss_100y | Structural building loss ($) for the 100-year return period |
| StructLoss_150y | Structural building loss ($) for the 150-year return period |
| StructLoss_200y | Structural building loss ($) for the 200-year return period |
| StructLoss_250y | Structural building loss ($) for the 250-year return period |
| StructLoss_475y | Structural building loss ($) for the 475-year return period |
| StructLoss_750y | Structural building loss ($) for the 750-year return period |
| StructLoss_975y | Structural building loss ($) for the 975-year return period |
| StructLoss_1500y | Structural building loss ($) for the 1500-year return period |
| StructLoss_2475y | Structural building loss ($) for the 2475-year return period |
| StructLoss_3000y | Structural building loss ($) for the 3000-year return period |
| NonStrLoss_10y | Non-structural building loss ($) for the 10-year return period |
| NonStrLoss_25y | Non-structural building loss ($) for the 25-year return period |
| NonStrLoss_50y | Non-structural building loss ($) for the 50-year return period |
| NonStrLoss_72y | Non-structural building loss ($) for the 72-year return period |
| NonStrLoss_100y | Non-structural building loss ($) for the 100-year return period |
| NonStrLoss_150y | Non-structural building loss ($) for the 150-year return period |
| NonStrLoss_200y | Non-structural building loss ($) for the 200-year return period |
| NonStrLoss_250y | Non-structural building loss ($) for the 250-year return period |
| NonStrLoss_475y | Non-structural building loss ($) for the 475-year return period |
| NonStrLoss_750y | Non-structural building loss ($) for the 750-year return period |
| NonStrLoss_975y | Non-structural building loss ($) for the 975-year return period |
| NonStrLoss_1500y | Non-structural building loss ($) for the 1500-year return period |
| NonStrLoss_2475y | Non-structural building loss ($) for the 2475-year return period |
| NonStrLoss_3000y | Non-structural building loss ($) for the 3000-year return period |
| building_loss_10y | Total building loss ($) for the 10-year return period |
| building_loss_25y | Total building loss ($) for the 25-year return period |
| building_loss_50y | Total building loss ($) for the 50-year return period |
| building_loss_72y | Total building loss ($) for the 72-year return period |
| building_loss_100y | Total building loss ($) for the 100-year return period |
| building_loss_150y | Total building loss ($) for the 150-year return period |
| building_loss_200y | Total building loss ($) for the 200-year return period |
| building_loss_250y | Total building loss ($) for the 250-year return period |
| building_loss_475y | Total building loss ($) for the 475-year return period |
| building_loss_750y | Total building loss ($) for the 750-year return period |
| building_loss_975y | Total building loss ($) for the 975-year return period |
| building_loss_1500y | Total building loss ($) for the 1500-year return period |
| building_loss_2475y | Total building loss ($) for the 2475-year return period |
| building_loss_3000y | Total building loss ($) for the 3000-year return period |
| content_loss_10y | Content loss ($) for the 10-year return period |
| content_loss_25y | Content loss ($) for the 25-year return period |
| content_loss_50y | Content loss ($) for the 50-year return period |
| content_loss_72y | Content loss ($) for the 72-year return period |
| content_loss_100y | Content loss ($) for the 100-year return period |
| content_loss_150y | Content loss ($) for the 150-year return period |
| content_loss_200y | Content loss ($) for the 200-year return period |
| content_loss_250y | Content loss ($) for the 250-year return period |
| content_loss_475y | Content loss ($) for the 475-year return period |
| content_loss_750y | Content loss ($) for the 750-year return period |
| content_loss_975y | Content loss ($) for the 975-year return period |
| content_loss_1500y | Content loss ($) for the 1500-year return period |
| content_loss_2475y | Content loss ($) for the 2475-year return period |
| content_loss_3000y | Content loss ($) for the 3000-year return period |
| inventory_loss_10y | Inventory loss ($) for the 10-year return period |
| inventory_loss_25y | Inventory loss ($) for the 25-year return period |
| inventory_loss_50y | Inventory loss ($) for the 50-year return period |
| inventory_loss_72y | Inventory loss ($) for the 72-year return period |
| inventory_loss_100y | Inventory loss ($) for the 100-year return period |
| inventory_loss_150y | Inventory loss ($) for the 150-year return period |
| inventory_loss_200y | Inventory loss ($) for the 200-year return period |
| inventory_loss_250y | Inventory loss ($) for the 250-year return period |
| inventory_loss_475y | Inventory loss ($) for the 475-year return period |
| inventory_loss_750y | Inventory loss ($) for the 750-year return period |
| inventory_loss_975y | Inventory loss ($) for the 975-year return period |
| inventory_loss_1500y | Inventory loss ($) for the 1500-year return period |
| inventory_loss_2475y | Inventory loss ($) for the 2475-year return period |
| inventory_loss_3000y | Inventory loss ($) for the 3000-year return period |
| relocation_loss_10y | Relocation loss ($) for the 10-year return period |
| relocation_loss_25y | Relocation loss ($) for the 25-year return period |
| relocation_loss_50y | Relocation loss ($) for the 50-year return period |
| relocation_loss_72y | Relocation loss ($) for the 72-year return period |
| relocation_loss_100y | Relocation loss ($) for the 100-year return period |
| relocation_loss_150y | Relocation loss ($) for the 150-year return period |
| relocation_loss_200y | Relocation loss ($) for the 200-year return period |
| relocation_loss_250y | Relocation loss ($) for the 250-year return period |
| relocation_loss_475y | Relocation loss ($) for the 475-year return period |
| relocation_loss_750y | Relocation loss ($) for the 750-year return period |
| relocation_loss_975y | Relocation loss ($) for the 975-year return period |
| relocation_loss_1500y | Relocation loss ($) for the 1500-year return period |
| relocation_loss_2475y | Relocation loss ($) for the 2475-year return period |
| relocation_loss_3000y | Relocation loss ($) for the 3000-year return period |
| income_loss_10y | Proprietor income loss ($) for the 10-year return period |
| income_loss_25y | Proprietor income loss ($) for the 25-year return period |
| income_loss_50y | Proprietor income loss ($) for the 50-year return period |
| income_loss_72y | Proprietor income loss ($) for the 72-year return period |
| income_loss_100y | Proprietor income loss ($) for the 100-year return period |
| income_loss_150y | Proprietor income loss ($) for the 150-year return period |
| income_loss_200y | Proprietor income loss ($) for the 200-year return period |
| income_loss_250y | Proprietor income loss ($) for the 250-year return period |
| income_loss_475y | Proprietor income loss ($) for the 475-year return period |
| income_loss_750y | Proprietor income loss ($) for the 750-year return period |
| income_loss_975y | Proprietor income loss ($) for the 975-year return period |
| income_loss_1500y | Proprietor income loss ($) for the 1500-year return period |
| income_loss_2475y | Proprietor income loss ($) for the 2475-year return period |
| income_loss_3000y | Proprietor income loss ($) for the 3000-year return period |
| rental_loss_10y | Rental loss ($) for the 10-year return period |
| rental_loss_25y | Rental loss ($) for the 25-year return period |
| rental_loss_50y | Rental loss ($) for the 50-year return period |
| rental_loss_72y | Rental loss ($) for the 72-year return period |
| rental_loss_100y | Rental loss ($) for the 100-year return period |
| rental_loss_150y | Rental loss ($) for the 150-year return period |
| rental_loss_200y | Rental loss ($) for the 200-year return period |
| rental_loss_250y | Rental loss ($) for the 250-year return period |
| rental_loss_475y | Rental loss ($) for the 475-year return period |
| rental_loss_750y | Rental loss ($) for the 750-year return period |
| rental_loss_975y | Rental loss ($) for the 975-year return period |
| rental_loss_1500y | Rental loss ($) for the 1500-year return period |
| rental_loss_2475y | Rental loss ($) for the 2475-year return period |
| rental_loss_3000y | Rental loss ($) for the 3000-year return period |
| wage_loss_10y | Wage loss ($) for the 10-year return period |
| wage_loss_25y | Wage loss ($) for the 25-year return period |
| wage_loss_50y | Wage loss ($) for the 50-year return period |
| wage_loss_72y | Wage loss ($) for the 72-year return period |
| wage_loss_100y | Wage loss ($) for the 100-year return period |
| wage_loss_150y | Wage loss ($) for the 150-year return period |
| wage_loss_200y | Wage loss ($) for the 200-year return period |
| wage_loss_250y | Wage loss ($) for the 250-year return period |
| wage_loss_475y | Wage loss ($) for the 475-year return period |
| wage_loss_750y | Wage loss ($) for the 750-year return period |
| wage_loss_975y | Wage loss ($) for the 975-year return period |
| wage_loss_1500y | Wage loss ($) for the 1500-year return period |
| wage_loss_2475y | Wage loss ($) for the 2475-year return period |
| wage_loss_3000y | Wage loss ($) for the 3000-year return period |
| total_economic_loss_10y | Total economic loss ($) for the 10-year return period |
| total_economic_loss_25y | Total economic loss ($) for the 25-year return period |
| total_economic_loss_50y | Total economic loss ($) for the 50-year return period |
| total_economic_loss_72y | Total economic loss ($) for the 72-year return period |
| total_economic_loss_100y | Total economic loss ($) for the 100-year return period |
| total_economic_loss_150y | Total economic loss ($) for the 150-year return period |
| total_economic_loss_200y | Total economic loss ($) for the 200-year return period |
| total_economic_loss_250y | Total economic loss ($) for the 250-year return period |
| total_economic_loss_475y | Total economic loss ($) for the 475-year return period |
| total_economic_loss_750y | Total economic loss ($) for the 750-year return period |
| total_economic_loss_975y | Total economic loss ($) for the 975-year return period |
| total_economic_loss_1500y | Total economic loss ($) for the 1500-year return period |
| total_economic_loss_2475y | Total economic loss ($) for the 2475-year return period |
| total_economic_loss_3000y | Total economic loss ($) for the 3000-year return period |

## LOSSES (AVERAGE ANNUALIZED LOSS)

| FIELD | DESCRIPTION |
|:---|:---|
| building_loss_aal | Building Average Annual Loss ($) |
| BldgAAL_lossratio_USDperM | Building Average Annual Loss Ratio ($ per $1 million building structure replacement cost) |
| content_loss_aal | Content Average Annual Loss ($) |
| inventory_loss_aal | Inventory Average Annual Loss ($) |
| relocation_loss_aal | Relocation Average Annual Loss ($) |
| income_loss_aal | Proprietor Income Average Annual Loss ($) |
| rental_loss_aal | Rental Average Annual Loss ($) |
| wage_loss_aal | Wage Average Annual Loss ($) |
| CapitalLoss_AAL | Capital Related (i.e., building+content+inventory) Average Annual Loss ($) |
| IncomeLoss_AAL | Income Related (i.e., relocation+proprietor income+rental+wage) Average Annual Loss ($) |
| TotalEconomicLoss_AAL | Total Economic (i.e., Capital+Income) Average Annual Loss ($) |

## LOSSES (ACTUARIAL LOSS)

| FIELD | DESCRIPTION |
|:---|:---|
| gross_building_loss_10yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 10-year return period |
| gross_building_loss_25yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 25-year return period |
| gross_building_loss_50yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 50-year return period |
| gross_building_loss_72yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 72-year return period |
| gross_building_loss_100yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 100-year return period |
| gross_building_loss_150yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 150-year return period |
| gross_building_loss_200yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 200-year return period |
| gross_building_loss_250yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 250-year return period |
| gross_building_loss_475yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 475-year return period |
| gross_building_loss_750yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 750-year return period |
| gross_building_loss_975yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 975-year return period |
| gross_building_loss_1500yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 1500-year return period |
| gross_building_loss_2475yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 2475-year return period |
| gross_building_loss_3000yr | Gross building (i.e., deductibles and limits applied) loss ($) for the 3000-year return period |
| gross_building_loss_aal | Gross building (i.e., deductibles and limits applied) Average Annual Loss ($) |
| GrossBldgAAL_LossRatio_USDperM | Gross building (i.e., deductibles and limits applied) Average Annual Loss Ratio ($ per $1 million building structure replacement cost) |
| gross_content_loss_aal | Gross content (i.e., deductibles and limits applied) Average Annual Loss ($) |

