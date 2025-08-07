from typing import Dict, List, Set, Any
import logging
import pandas as pd

class FieldMapping():
    """
    Generic mapping class for data fields with input/output field separation.
    
    Provides strong typing support and alias matching for automatic discovery.
    Input fields use alias mechanism, output fields use internal names directly.
    """

    def __init__(
        self, 
        df: pd.DataFrame, 
        aliases: Dict[str, List[str]],
        output_fields: Dict[str, str],
        overrides: Dict[str, str] | None = None
    ) -> None:
        self._aliases = aliases
        self._output_fields = output_fields
        self._input_fields = set(self._aliases.keys())
        self._overrides = overrides or {}
        
        # Initialize values dictionary - maps internal property names to actual column names
        self._values = {}
        
        # Discover mappings automatically
        discovered = self.discover_mappings(df)
        self._values.update(discovered)

    def find_best_match(self, df_columns: List[str], property_name: str) -> str | None:
        """
        Find the best matching column for a property.
        
        Priority order:
        1. Override (if provided, always takes precedence)
        2. Alias matches for input fields (in order of preference, case-insensitive)
        3. Direct name match for output fields (case-insensitive)
        
        Note: This method only returns matches found in the DataFrame columns.
        Fallback values are handled in discover_mappings.
        """
        # Create case-insensitive column lookup
        lower_cols = [col.lower() for col in df_columns]
        col_dict = {col.lower(): col for col in df_columns}
        
        # 1. If there's an override and it exists in columns, use it
        if self._overrides and property_name in self._overrides:
            override_value = self._overrides[property_name]
            if override_value.lower() in lower_cols:
                return col_dict[override_value.lower()]
            else:
                return None
        
        # 2. For input fields, try aliases in order of preference
        if property_name in self._input_fields:
            for alias in self._aliases[property_name]:
                if alias.lower() in lower_cols:
                    return col_dict[alias.lower()]
        
        # 3. For output fields, try direct name match
        elif property_name in self._output_fields:
            internal_name = self._output_fields[property_name]
            if internal_name.lower() in lower_cols:
                return col_dict[internal_name.lower()]
        
        # No match found
        return None

    def discover_mappings(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Discover field mappings in a DataFrame.
        
        Returns:
            Dictionary mapping internal property names to discovered external column names
        
        Raises:
            ValueError: If required input fields are not found
        """
        discovered = {}
        missing_input_fields = []
        
        # Check input fields first - these are required
        for prop in self._input_fields:
            match = self.find_best_match(list(df.columns), prop)
            if match:
                discovered[prop] = match
            else:
                # If no match found, use the first alias as fallback
                if self._aliases[prop]:
                    discovered[prop] = self._aliases[prop][0]
                else:
                    missing_input_fields.append(prop)
        
        # Raise error if any input fields are missing and have no aliases
        if missing_input_fields:
            logging.info(f"Required input fields not found in DataFrame and have no aliases: {missing_input_fields}")
        
        # Check output fields - these are optional
        for prop in self._output_fields.keys():
            match = self.find_best_match(list(df.columns), prop)
            if match:
                discovered[prop] = match
            else:
                # If no match found, use the value from output_fields as fallback
                discovered[prop] = self._output_fields[prop]
        
        # Apply overrides last to ensure they take precedence
        for prop, override_value in self._overrides.items():
            discovered[prop] = override_value
        
        return discovered

    def set_field_mapping(self, property_name: str, column_name: str) -> None:
        """Manually set a field mapping (acts as override)."""
        self._values[property_name] = column_name

    @property
    def input_fields(self) -> Set[str]:
        """Get set of input field names."""
        return self._input_fields
    
    @property
    def output_fields(self) -> Set[str]:
        """Get set of output field names."""
        return set(self._output_fields.keys())

    def get_field_name(self, property_name: str) -> str | None:
        """Retrieves the field name for the given internal property name."""
        return self._values.get(property_name)
