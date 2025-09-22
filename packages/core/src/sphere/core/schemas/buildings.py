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
            "first_floor_height": ["first_floor_height", "found_ht", "first_floor_ht", "ffh", "floor_height"],
            "foundation_type": ["foundation_type", "fndtype", "found_type", "fnd_type"],
            "number_stories": ["number_stories", "num_story", "numstories", "stories", "num_floors", "floors"],
            "area": ["area", "sqft", "building_area", "floor_area"],
            "building_cost": ["buildingcostusd", "building_cost", "val_struct", "cost", "replacement_cost", "building_value"],
            "content_cost": ["contentcostusd", "content_cost", "val_cont", "contents_cost"],
            "inventory_cost": ["inventorycostusd", "inventory_cost", "val_inv", "inv_cost"],
            "eq_building_type": ["eqbldgtypeid", "eq_building_type", "earthquake_building_type"],
            "eq_design_level": ["eqdesignlevelid", "eq_design_level", "design_level"], 
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
