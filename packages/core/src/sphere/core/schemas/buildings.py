from typing import Dict, Any
import geopandas as gpd
import pandas as pd
from sphere.core.schemas.field_mapping import FieldMapping

class Buildings:
    """
    Base class for building-related data with field mapping and data access.
    """
    
    def __init__(self, gdf: gpd.GeoDataFrame, overrides: Dict[str, str] | None = None):
        self._gdf = gdf
        
        # Define building-specific aliases (all lowercase for case-insensitive matching)
        aliases = {
            "id": ["id", "building_id", "bldg_id", "fd_id"],
            "occupancy_type": ["occupancy_type", "occtype", "occupancy", "occ_type", "building_type"],
            "first_floor_height": ["first_floor_height", "found_ht", "first_floor_ht", "ffh", "floor_height", "FirstFloor"],
            "foundation_type": ["foundation_type", "fndtype", "found_type", "fnd_type"],
            "number_stories": ["number_stories", "num_story", "numstories", "stories", "num_floors", "floors"],
            "area": ["area", "sqft", "building_area", "floor_area"],
            "building_cost": ["buildingcostusd", "building_cost", "hazus_building_values", "val_struct", "cost", "replacement_cost", "building_value"],
            "content_cost": ["contentcostusd", "content_cost", "hazus_content_values", "val_cont", "contents_cost"],
            "inventory_cost": ["inventorycostusd", "inventory_cost", "val_inv", "inv_cost"],
            "eq_building_type": ["eqbldgtypeid", "eqbldgtypeid_si", "eq_building_type", "earthquake_building_type"],
            "eq_design_level": ["eqdesignlevelid", "eqdesignlevelid_si", "eq_design_level", "design_level"], 
            "probability_str_complete": ["probability_str_complete", "p_str_comp", "prob_str_complete"],
            "probability_str_none": ["probability_str_none", "p_str_none", "prob_str_none"],
            "probability_str_moderate": ["probability_str_moderate", "p_str_mod", "prob_str_moderate"],
            "probability_str_extensive": ["probability_str_extensive", "p_str_ext", "prob_str_extensive"],
            # "probability_nsd_exceed_moderate": ["probability_nsd_exceed_moderate"],
            # "probability_nsd_exceed_extensive": ["probability_nsd_exceed_extensive"],
            "probability_nsd_complete": ["probability_nsd_complete", "p_nsd_comp", "prob_nsd_complete"],
            "probability_nsd_none": ["probability_nsd_none", "p_nsd_none", "prob_nsd_none"],
            "probability_nsd_moderate": ["probability_nsd_moderate", "p_nsd_mod", "prob_nsd_moderate"],
            "probability_nsd_extensive": ["probability_nsd_extensive", "p_nsd_ext", "prob_nsd_extensive"],
            "probability_content_exceed_moderate": ["probability_content_exceed_moderate"],
            "probability_content_exceed_extensive": ["probability_content_exceed_extensive"],
            "probability_content_complete": ["probability_content_complete", "p_cont_comp", "prob_cont_complete"],
            "probability_content_none": ["probability_content_none", "p_cont_none", "prob_cont_none"],
            "probability_content_moderate": ["probability_content_moderate", "p_cont_mod", "prob_cont_moderate"],
            "probability_content_extensive": ["probability_content_extensive", "p_cont_ext", "prob_cont_extensive"],
            "relocation_loss": ["relocation_loss", "relocationlossusd", "reloc_loss", "reloc_loss_usd"],
            "income_loss": ["income_loss", "incomelossusd", "inc_loss", "inc_loss_usd"],
            "rental_loss": ["rental_loss", "rentallossusd", "rent_loss", "rent_loss_usd"],
            "wage_loss": ["wage_loss", "wagelossusd", "wage_loss", "wage_loss_usd"],
            "building_loss": ["building_loss", "bldglossusd"],
            "content_loss": ["content_loss", "contentlossusd"],
            # "inventory_loss": ["inventory_loss"],
            #"flood_type": ["floodtype", "flood_type", "flooding_type"],
        }
        
        # Define output fields
        output_fields = {
            "flux": "flux",
            "flood_depth": "flood_depth",
            "depth_in_structure": "depth_in_structure",
            "bddf_id": "bddf_id",
            "building_damage_percent": "building_damage_percent",
            "building_loss": "building_loss",
            "cddf_id": "cddf_id",
            "content_damage_percent": "content_damage_percent",
            "content_loss": "content_loss",
            "iddf_id": "iddf_id",
            "inventory_damage_percent": "inventory_damage_percent",
            "inventory_loss": "inventory_loss",
            "relocation_loss": "relocation_loss",
            "income_loss": "income_loss",
            "rental_loss": "rental_loss",
            "wage_loss": "wage_loss",
            "debris_finish": "debris_finish",
            "debris_foundation": "debris_foundation",
            "debris_structure": "debris_structure",
            "debris_total": "debris_total",
            "restoration_minimum": "restoration_minimum",
            "restoration_maximum": "restoration_maximum",
            # Tsunami probability fields
            "probability_str_exceed_moderate": "probability_str_exceed_moderate",
            "probability_str_exceed_extensive": "probability_str_exceed_extensive", 
            "probability_str_complete": "probability_str_complete",
            "probability_str_none": "probability_str_none",
            "probability_str_moderate": "probability_str_moderate",
            "probability_str_extensive": "probability_str_extensive",
            "probability_nsd_exceed_moderate": "probability_nsd_exceed_moderate",
            "probability_nsd_exceed_extensive": "probability_nsd_exceed_extensive",
            "probability_nsd_complete": "probability_nsd_complete",
            "probability_nsd_none": "probability_nsd_none",
            "probability_nsd_moderate": "probability_nsd_moderate",
            "probability_nsd_extensive": "probability_nsd_extensive",
            "probability_content_exceed_moderate": "probability_content_exceed_moderate",
            "probability_content_exceed_extensive": "probability_content_exceed_extensive",
            "probability_content_complete": "probability_content_complete",
            "probability_content_none": "probability_content_none",
            "probability_content_moderate": "probability_content_moderate",
            "probability_content_extensive": "probability_content_extensive",
        }
        
        self.fields = FieldMapping(gdf, aliases, output_fields, overrides)

        # Ensure damage-function ID output columns exist on the GeoDataFrame
        for df_prop in ("bddf_id", "cddf_id", "iddf_id"):
            col_name = self.fields.get_field_name(df_prop)
            if col_name and col_name not in self._gdf.columns:
                self._gdf[col_name] = None

    @property
    def gdf(self) -> gpd.GeoDataFrame:
        """Get the underlying GeoDataFrame."""
        return self._gdf

    def _ensure_output_field(self, property_name: str) -> str:
        """Ensure output field exists in the GeoDataFrame and return its name."""
        field_name = self.fields.get_field_name(property_name)
        if field_name and field_name not in self._gdf.columns:
            self._gdf[field_name] = pd.NA
        return field_name

    # Input Fields - assume they exist (FieldMapping validates this)
    @property
    def id(self) -> pd.Series:
        field_name = self.fields.get_field_name("id")
        return self._gdf[field_name]

    @property
    def occupancy_type(self) -> pd.Series:
        field_name = self.fields.get_field_name("occupancy_type")
        return self._gdf[field_name]

    @property
    def first_floor_height(self) -> pd.Series:
        field_name = self.fields.get_field_name("first_floor_height")
        return self._gdf[field_name]

    @property
    def foundation_type(self) -> pd.Series:
        field_name = self.fields.get_field_name("foundation_type")
        return self._gdf[field_name]

    @property
    def number_stories(self) -> pd.Series:
        field_name = self.fields.get_field_name("number_stories")
        return self._gdf[field_name]

    @property
    def area(self) -> pd.Series:
        field_name = self.fields.get_field_name("area")
        return self._gdf[field_name]

    @property
    def building_cost(self) -> pd.Series:
        field_name = self.fields.get_field_name("building_cost")
        return self._gdf[field_name]

    @property
    def content_cost(self) -> pd.Series:
        field_name = self.fields.get_field_name("content_cost")
        return self._gdf[field_name]

    @property
    def inventory_cost(self) -> pd.Series:
        field_name = self.fields.get_field_name("inventory_cost")
        return self._gdf[field_name]

    @property
    def eq_building_type(self) -> pd.Series:
        field_name = self.fields.get_field_name("eq_building_type")
        return self._gdf[field_name]

    @property
    def eq_design_level(self) -> pd.Series:
        field_name = self.fields.get_field_name("eq_design_level")
        return self._gdf[field_name]

    @property
    def flood_type(self) -> pd.Series:
        field_name = self.fields.get_field_name("flood_type")
        return self._gdf[field_name]

    # Output Fields - create if they don't exist
    @property
    def flux(self) -> pd.Series:
        field_name = self._ensure_output_field("flux")
        return self._gdf[field_name]
    
    @flux.setter
    def flux(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("flux")
        self._gdf[field_name] = value

    @property
    def flood_depth(self) -> pd.Series:
        field_name = self._ensure_output_field("flood_depth")
        return self._gdf[field_name]
    
    @flood_depth.setter
    def flood_depth(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("flood_depth")
        self._gdf[field_name] = value
    
    @property
    def depth_in_structure(self) -> pd.Series:
        field_name = self._ensure_output_field("depth_in_structure")
        return self._gdf[field_name]
    
    @depth_in_structure.setter
    def depth_in_structure(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("depth_in_structure")
        self._gdf[field_name] = value

    @property
    def bddf_id(self) -> pd.Series:
        field_name = self._ensure_output_field("bddf_id")
        return self._gdf[field_name]
    
    @bddf_id.setter
    def bddf_id(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("bddf_id")
        self._gdf[field_name] = value

    @property
    def building_damage_percent(self) -> pd.Series:
        field_name = self._ensure_output_field("building_damage_percent")
        return self._gdf[field_name]
    
    @building_damage_percent.setter
    def building_damage_percent(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("building_damage_percent")
        self._gdf[field_name] = value

    @property
    def building_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("building_loss")
        return self._gdf[field_name]
    
    @building_loss.setter
    def building_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("building_loss")
        self._gdf[field_name] = value

    @property
    def cddf_id(self) -> pd.Series:
        field_name = self._ensure_output_field("cddf_id")
        return self._gdf[field_name]
    
    @cddf_id.setter
    def cddf_id(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("cddf_id")
        self._gdf[field_name] = value

    @property
    def content_damage_percent(self) -> pd.Series:
        field_name = self._ensure_output_field("content_damage_percent")
        return self._gdf[field_name]
    
    @content_damage_percent.setter
    def content_damage_percent(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("content_damage_percent")
        self._gdf[field_name] = value

    @property
    def content_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("content_loss")
        return self._gdf[field_name]
    
    @content_loss.setter
    def content_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("content_loss")
        self._gdf[field_name] = value

    @property
    def iddf_id(self) -> pd.Series:
        field_name = self._ensure_output_field("iddf_id")
        return self._gdf[field_name]
    
    @iddf_id.setter
    def iddf_id(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("iddf_id")
        self._gdf[field_name] = value

    @property
    def inventory_damage_percent(self) -> pd.Series:
        field_name = self._ensure_output_field("inventory_damage_percent")
        return self._gdf[field_name]
    
    @inventory_damage_percent.setter
    def inventory_damage_percent(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("inventory_damage_percent")
        self._gdf[field_name] = value

    @property
    def inventory_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("inventory_loss")
        return self._gdf[field_name]
    
    @inventory_loss.setter
    def inventory_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("inventory_loss")
        self._gdf[field_name] = value

    @property
    def relocation_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("relocation_loss")
        return self._gdf[field_name]
    
    @relocation_loss.setter
    def relocation_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("relocation_loss")
        self._gdf[field_name] = value
    
    @property
    def income_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("income_loss")
        return self._gdf[field_name]
    
    @income_loss.setter
    def income_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("income_loss")
        self._gdf[field_name] = value
    
    @property
    def wage_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("wage_loss")
        return self._gdf[field_name]
    
    @wage_loss.setter
    def wage_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("wage_loss")
        self._gdf[field_name] = value

    @property
    def rental_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("rental_loss")
        return self._gdf[field_name]
    
    @rental_loss.setter
    def rental_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("rental_loss")
        self._gdf[field_name] = value
    
    @property
    def debris_finish(self) -> pd.Series:
        field_name = self._ensure_output_field("debris_finish")
        return self._gdf[field_name]
    
    @debris_finish.setter
    def debris_finish(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("debris_finish")
        self._gdf[field_name] = value

    @property
    def debris_foundation(self) -> pd.Series:
        field_name = self._ensure_output_field("debris_foundation")
        return self._gdf[field_name]
    
    @debris_foundation.setter
    def debris_foundation(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("debris_foundation")
        self._gdf[field_name] = value

    @property
    def debris_structure(self) -> pd.Series:
        field_name = self._ensure_output_field("debris_structure")
        return self._gdf[field_name]
    
    @debris_structure.setter
    def debris_structure(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("debris_structure")
        self._gdf[field_name] = value

    @property
    def debris_total(self) -> pd.Series:
        field_name = self._ensure_output_field("debris_total")
        return self._gdf[field_name]
    
    @debris_total.setter
    def debris_total(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("debris_total")
        self._gdf[field_name] = value
    
    @property
    def restoration_minimum(self) -> pd.Series:
        field_name = self._ensure_output_field("restoration_minimum")
        return self._gdf[field_name]
    
    @restoration_minimum.setter
    def restoration_minimum(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("restoration_minimum")
        self._gdf[field_name] = value
    
    @property
    def restoration_maximum(self) -> pd.Series:
        field_name = self._ensure_output_field("restoration_maximum")
        return self._gdf[field_name]
    
    @restoration_maximum.setter
    def restoration_maximum(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("restoration_maximum")
        self._gdf[field_name] = value
        
    # Probability fields properties
    @property
    def probability_str_exceed_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_exceed_moderate")
        return self._gdf[field_name]
    
    @probability_str_exceed_moderate.setter
    def probability_str_exceed_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_exceed_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_str_exceed_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_exceed_extensive")
        return self._gdf[field_name]
    
    @probability_str_exceed_extensive.setter
    def probability_str_exceed_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_exceed_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_str_complete(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_complete")
        return self._gdf[field_name]
    
    @probability_str_complete.setter
    def probability_str_complete(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_complete")
        self._gdf[field_name] = value
        
    @property
    def probability_str_none(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_none")
        return self._gdf[field_name]
    
    @probability_str_none.setter
    def probability_str_none(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_none")
        self._gdf[field_name] = value
        
    @property
    def probability_str_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_moderate")
        return self._gdf[field_name]
    
    @probability_str_moderate.setter
    def probability_str_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_str_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_extensive")
        return self._gdf[field_name]
    
    @probability_str_extensive.setter
    def probability_str_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_exceed_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_exceed_moderate")
        return self._gdf[field_name]
    
    @probability_nsd_exceed_moderate.setter
    def probability_nsd_exceed_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_exceed_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_exceed_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_exceed_extensive")
        return self._gdf[field_name]
    
    @probability_nsd_exceed_extensive.setter
    def probability_nsd_exceed_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_exceed_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_complete(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_complete")
        return self._gdf[field_name]
    
    @probability_nsd_complete.setter
    def probability_nsd_complete(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_complete")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_none(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_none")
        return self._gdf[field_name]
    
    @probability_nsd_none.setter
    def probability_nsd_none(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_none")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_moderate")
        return self._gdf[field_name]
    
    @probability_nsd_moderate.setter
    def probability_nsd_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_extensive")
        return self._gdf[field_name]
    
    @probability_nsd_extensive.setter
    def probability_nsd_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_content_exceed_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_exceed_moderate")
        return self._gdf[field_name]
    
    @probability_content_exceed_moderate.setter
    def probability_content_exceed_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_exceed_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_content_exceed_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_exceed_extensive")
        return self._gdf[field_name]
    
    @probability_content_exceed_extensive.setter
    def probability_content_exceed_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_exceed_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_content_complete(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_complete")
        return self._gdf[field_name]
    
    @probability_content_complete.setter
    def probability_content_complete(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_complete")
        self._gdf[field_name] = value
        
    @property
    def probability_content_none(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_none")
        return self._gdf[field_name]
    
    @probability_content_none.setter
    def probability_content_none(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_none")
        self._gdf[field_name] = value
        
    @property
    def probability_content_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_moderate")
        return self._gdf[field_name]
    
    @probability_content_moderate.setter
    def probability_content_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_content_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_extensive")
        return self._gdf[field_name]
    
    @probability_content_extensive.setter
    def probability_content_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_extensive")
        self._gdf[field_name] = value

class ttfBuildings:
    """
    Base class for TTF building-related data with field mapping and data access.
    """
    
    def __init__(self, gdf: gpd.GeoDataFrame, overrides: Dict[str, str] | None = None):
        self._gdf = gdf
        
        # Define TTF building-specific aliases (all lowercase for case-insensitive matching)
        aliases = {
            "id": ["id", "nsiid"],
            # "momflux": ["momflux", "flow_momentum", "momentum_flux"],
            # "flowdepth": ["flowdepth", "flood_depth", "water_depth", "depth"],
            "area": ["areasqft", "area", "sqft", "building_area", "floor_area"],
            "building_cost": ["buildingcostusd", "building_cost", "hazus_building_values", "val_struct", "cost", "replacement_cost", "building_value", "valstruct"],
            "content_cost": ["contentcostusd", "content_cost", "hazus_content_values", "val_cont", "contents_cost", "valcont"],
            "inventory_cost": ["inventorycostusd", "inventory_cost", "val_inv", "inv_cost"],
            "first_floor_height": ["first_floor_height", "found_ht", "first_floor_ht", "ffh", "floor_height", "firstfloor"],
            "eq_building_type": ["eqbldgtypeid", "eqbldgtypeid_si", "eq_building_type", "earthquake_building_type", "eqbldgtype"],
            "eq_design_level": ["eqdesignlevelid", "eqdesignlevelid_si", "eq_design_level", "design_level", "eqdesignle"],
            "occupancy_type": ["occupancy_type", "occtype", "occupancy", "occ_type", "building_type"],
        }
        
        # Define output fields
        output_fields = {
            "NsiID": "NsiID",
            "building_loss_aal": "building_loss_aal",
            "content_loss_aal": "content_loss_aal",
            "relocation_loss_aal": "relocation_loss_aal",
            "income_loss_aal": "income_loss_aal",
            "rental_loss_aal": "rental_loss_aal",
            "wage_loss_aal": "wage_loss_aal",
            "gross_building_loss_aal": "gross_building_loss_aal",
            "gross_content_loss_aal": "gross_content_loss_aal",
        }

        # Grab all fields from gdf columns that start with "MomFlux" or "FlowDepth"
        import re
        flux_return_list = []
        flood_return_list = []
        for col in gdf.columns:
            if col.lower().startswith("momflux"):
                output_fields[col] = col
                # Use regex to create an alias where the key value is "momflux" + the return period (e.g., "momflux100")
                match = re.match(r"(momflux_)(\d+yr)", col.lower())
                # if match:
                #     alias_key = f"{match.group(1)}{match.group(2)}"
                #     aliases[alias_key] = [col]
                flux_return_list.append(col)
            elif col.lower().startswith("flowdepth"):
                output_fields[col] = col
                # Use regex to create an alias where the key value is "flowdepth" + the return period (e.g., "flowdepth100")
                match = re.match(r"(flowdepth_)(\d+yr)", col.lower())
                # if match:
                #     alias_key = f"{match.group(1)}{match.group(2)}"
                #     aliases[alias_key] = [col]
                flood_return_list.append(col)
        aliases["flux"] = [flux_return_list]
        aliases["flood_depth"] = [flood_return_list]
            
        # Check that momflux and flowdepth have same return periods
        if len(flux_return_list) != len(flood_return_list):
            raise ValueError("Mismatch between MomFlux and FlowDepth return periods in GeoDataFrame columns.")
        else:
            # Create building loss and content loss output fields based on return periods
            return_periods = [re.search(r'(\d+yr)', item.lower()).group(1) for item in flux_return_list]
            bldg_loss_list = ["building_loss_" + rp for rp in return_periods]
            cont_loss_list = ["content_loss_" + rp for rp in return_periods]
            reloc_loss_list = ["relocation_loss_" + rp for rp in return_periods]
            income_loss_list = ["income_loss_" + rp for rp in return_periods]
            rental_loss_list = ["rental_loss_" + rp for rp in return_periods]
            wage_loss_list = ["wage_loss_" + rp for rp in return_periods]
            str_comp_list = ["p_str_comp_" + rp for rp in return_periods]
            str_none_list = ["p_str_none_" + rp for rp in return_periods]
            str_mod_list = ["p_str_mod_" + rp for rp in return_periods]
            str_ext_list = ["p_str_ext_" + rp for rp in return_periods]
            nsd_comp_list = ["p_nsd_comp_" + rp for rp in return_periods]
            nsd_none_list = ["p_nsd_none_" + rp for rp in return_periods]
            nsd_mod_list = ["p_nsd_mod_" + rp for rp in return_periods]
            nsd_ext_list = ["p_nsd_ext_" + rp for rp in return_periods]
            cont_comp_list = ["p_cont_comp_" + rp for rp in return_periods]
            cont_none_list = ["p_cont_none_" + rp for rp in return_periods]  
            cont_mod_list = ["p_cont_mod_" + rp for rp in return_periods]    
            cont_ext_list = ["p_cont_ext_" + rp for rp in return_periods]    
            aliases["probability_str_complete"] = [str_comp_list]
            aliases["probability_str_none"] = [str_none_list]
            aliases["probability_str_moderate"] = [str_mod_list]
            aliases["probability_str_extensive"] = [str_ext_list]
            aliases["probability_nsd_complete"] = [nsd_comp_list]
            aliases["probability_nsd_none"] = [nsd_none_list]
            aliases["probability_nsd_moderate"] = [nsd_mod_list]
            aliases["probability_nsd_extensive"] = [nsd_ext_list]
            aliases["probability_content_complete"] = [cont_comp_list]
            aliases["probability_content_none"] = [cont_none_list]
            aliases["probability_content_moderate"] = [cont_mod_list]
            aliases["probability_content_extensive"] = [cont_ext_list]
            aliases["building_loss"] = [bldg_loss_list]
            aliases["content_loss"] = [cont_loss_list]
            aliases["relocation_loss"] = [reloc_loss_list]
            aliases["income_loss"] = [income_loss_list]
            aliases["rental_loss"] = [rental_loss_list]
            aliases["wage_loss"] = [wage_loss_list]
            for building, content, relocation, rent, wage in zip(bldg_loss_list, cont_loss_list, reloc_loss_list, rental_loss_list, wage_loss_list):
                output_fields[building] = building
                output_fields[content] = content
                output_fields[relocation] = relocation
                output_fields[rent] = rent
                output_fields[wage] = wage
        self._gdf["Occupancy_Type"] = self._gdf["NsiID"].str.split(' ', expand=True)[0]

        self.flux_return_list = flux_return_list
        self.flood_return_list = flood_return_list
        self.str_comp_list = str_comp_list
        self.str_none_list = str_none_list
        self.str_mod_list = str_mod_list
        self.str_ext_list = str_ext_list
        self.nsd_comp_list = nsd_comp_list
        self.nsd_none_list = nsd_none_list
        self.nsd_mod_list = nsd_mod_list
        self.nsd_ext_list = nsd_ext_list
        self.cont_comp_list = cont_comp_list
        self.cont_none_list = cont_none_list
        self.cont_mod_list = cont_mod_list
        self.cont_ext_list = cont_ext_list
        self.fields = FieldMapping(gdf, aliases, output_fields, overrides)

    @property
    def gdf(self) -> gpd.GeoDataFrame:
        """Get the underlying GeoDataFrame."""
        return self._gdf
    
    def _ensure_output_field(self, *property_names: str) -> str:
        """Ensure output field exists in the GeoDataFrame and return its name."""
        field_names = []
        for property_name in property_names:
            field_name = self.fields.get_field_name(property_name)
            if field_name and field_name not in self._gdf.columns:
                self._gdf[field_name] = pd.NA
            field_names.append(field_name)
        return field_names
    
    # Input Fields - assume they exist (FieldMapping validates this)
    @property
    def id(self) -> pd.Series:
        field_name = self.fields.get_field_name("id")
        return self._gdf[field_name]
    
    @property
    def occupancy_type(self) -> pd.Series:
        field_name = self.fields.get_field_name("occupancy_type")
        return self._gdf[field_name]
    
    @property
    def first_floor_height(self) -> pd.Series:
        field_name = self.fields.get_field_name("first_floor_height")
        return self._gdf[field_name]
    
    @property
    def foundation_type(self) -> pd.Series:
        field_name = self.fields.get_field_name("foundation_type")
        return self._gdf[field_name]
    
    @property
    def number_stories(self) -> pd.Series:
        field_name = self.fields.get_field_name("number_stories")
        return self._gdf[field_name]
    
    @property
    def area(self) -> pd.Series:
        field_name = self.fields.get_field_name("area")
        return self._gdf[field_name]
    
    @property
    def building_cost(self) -> pd.Series:
        field_name = self.fields.get_field_name("building_cost")
        return self._gdf[field_name]
    
    @property
    def content_cost(self) -> pd.Series:
        field_name = self.fields.get_field_name("content_cost")
        return self._gdf[field_name]
    
    # Probability fields properties
    @property
    def probability_str_exceed_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_exceed_moderate")
        return self._gdf[field_name]
    
    @probability_str_exceed_moderate.setter
    def probability_str_exceed_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_exceed_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_str_exceed_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_str_exceed_extensive")
        return self._gdf[field_name]
    
    @probability_str_exceed_extensive.setter
    def probability_str_exceed_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_str_exceed_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_str_complete(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.str_comp_list)
        return self._gdf[field_name]
    
    @probability_str_complete.setter
    def probability_str_complete(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.str_comp_list)
        self._gdf[field_name] = value
        
    @property
    def probability_str_none(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.str_none_list)
        return self._gdf[field_name]
    
    @probability_str_none.setter
    def probability_str_none(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.str_none_list)
        self._gdf[field_name] = value
        
    @property
    def probability_str_moderate(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.str_mod_list)
        return self._gdf[field_name]
    
    @probability_str_moderate.setter
    def probability_str_moderate(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.str_mod_list)
        self._gdf[field_name] = value
        
    @property
    def probability_str_extensive(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.str_ext_list)
        return self._gdf[field_name]
    
    @probability_str_extensive.setter
    def probability_str_extensive(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.str_ext_list)
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_exceed_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_exceed_moderate")
        return self._gdf[field_name]
    
    @probability_nsd_exceed_moderate.setter
    def probability_nsd_exceed_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_exceed_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_exceed_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_nsd_exceed_extensive")
        return self._gdf[field_name]
    
    @probability_nsd_exceed_extensive.setter
    def probability_nsd_exceed_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_nsd_exceed_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_complete(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.nsd_comp_list)
        return self._gdf[field_name]
    
    @probability_nsd_complete.setter
    def probability_nsd_complete(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.nsd_comp_list)
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_none(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.nsd_none_list)
        return self._gdf[field_name]
    
    @probability_nsd_none.setter
    def probability_nsd_none(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.nsd_none_list)
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_moderate(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.nsd_mod_list)
        return self._gdf[field_name]
    
    @probability_nsd_moderate.setter
    def probability_nsd_moderate(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.nsd_mod_list)
        self._gdf[field_name] = value
        
    @property
    def probability_nsd_extensive(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.nsd_ext_list)
        return self._gdf[field_name]
    
    @probability_nsd_extensive.setter
    def probability_nsd_extensive(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.nsd_ext_list)
        self._gdf[field_name] = value
        
    @property
    def probability_content_exceed_moderate(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_exceed_moderate")
        return self._gdf[field_name]
    
    @probability_content_exceed_moderate.setter
    def probability_content_exceed_moderate(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_exceed_moderate")
        self._gdf[field_name] = value
        
    @property
    def probability_content_exceed_extensive(self) -> pd.Series:
        field_name = self._ensure_output_field("probability_content_exceed_extensive")
        return self._gdf[field_name]
    
    @probability_content_exceed_extensive.setter
    def probability_content_exceed_extensive(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("probability_content_exceed_extensive")
        self._gdf[field_name] = value
        
    @property
    def probability_content_complete(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.cont_comp_list)
        return self._gdf[field_name]
    
    @probability_content_complete.setter
    def probability_content_complete(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.cont_comp_list)
        self._gdf[field_name] = value
        
    @property
    def probability_content_none(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.cont_none_list)
        return self._gdf[field_name]
    
    @probability_content_none.setter
    def probability_content_none(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.cont_none_list)
        self._gdf[field_name] = value
        
    @property
    def probability_content_moderate(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.cont_mod_list)
        return self._gdf[field_name]
    
    @probability_content_moderate.setter
    def probability_content_moderate(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.cont_mod_list)
        self._gdf[field_name] = value
        
    @property
    def probability_content_extensive(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(self.cont_ext_list)
        return self._gdf[field_name]
    
    @probability_content_extensive.setter
    def probability_content_extensive(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(self.cont_ext_list)
        self._gdf[field_name] = value
    # Output Fields - create if they don't exist
    @property
    def flux(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(*self.flux_return_list)
        return self._gdf[field_name]
    
    @flux.setter
    def flux(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(*self.flux_return_list)
        self._gdf[field_name] = value
    
    @property
    def flood_depth(self) -> pd.DataFrame:
        field_name = self._ensure_output_field(*self.flood_return_list)
        return self._gdf[field_name]
    
    @flood_depth.setter
    def flood_depth(self, value: pd.DataFrame) -> None:
        field_name = self._ensure_output_field(*self.flood_return_list)
        self._gdf[field_name] = value

    @property
    def building_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("building_loss")
        return self._gdf[field_name]
    
    @building_loss.setter
    def building_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("building_loss")
        self._gdf[field_name] = value

    @property
    def content_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("content_loss")
        return self._gdf[field_name]

    @content_loss.setter
    def content_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("content_loss")
        self._gdf[field_name] = value

    @property
    def relocation_loss(self) -> pd.Series:
        field_name = self._ensure_output_field("relocation_loss")
        return self._gdf[field_name]

    @relocation_loss.setter
    def relocation_loss(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("relocation_loss")
        self._gdf[field_name] = value

    @property
    def building_loss_aal(self) -> pd.Series:
        field_name = self._ensure_output_field("building_loss_aal")
        return self._gdf[field_name]
    
    @building_loss_aal.setter
    def building_loss_aal(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("building_loss_aal")
        self._gdf[field_name] = value

    @property
    def content_loss_aal(self) -> pd.Series:
        field_name = self._ensure_output_field("content_loss_aal")
        return self._gdf[field_name]
    
    @content_loss_aal.setter
    def content_loss_aal(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("content_loss_aal")
        self._gdf[field_name] = value
    
    @property
    def gross_building_loss_aal(self) -> pd.Series:
        field_name = self._ensure_output_field("gross_building_loss_aal")
        return self._gdf[field_name]
    
    @gross_building_loss_aal.setter
    def gross_building_loss_aal(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("gross_building_loss_aal")
        self._gdf[field_name] = value

    @property
    def gross_content_loss_aal(self) -> pd.Series:
        field_name = self._ensure_output_field("gross_content_loss_aal")
        return self._gdf[field_name]
    
    @gross_content_loss_aal.setter
    def gross_content_loss_aal(self, value: pd.Series) -> None:
        field_name = self._ensure_output_field("gross_content_loss_aal")
        self._gdf[field_name] = value