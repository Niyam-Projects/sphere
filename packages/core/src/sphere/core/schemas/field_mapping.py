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
        overrides: Dict[str, str] | None = None,
        required_fields: List[str] | None = None,
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

        # Validate required fields are resolvable to actual DataFrame columns
        if required_fields:
            missing = self.get_missing_required_fields(df, required_fields)
            if missing:
                raise ValueError(
                    "Required input fields not found in DataFrame:\n" +
                    "\n".join(f"  {m}" for m in missing)
                )

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

        def map_lower(alias_list: List[str]) -> List[str]:
            """Helper to create a lower-cased version of alias list for case-insensitive matching."""
            # Check if items in alias_list are strings or lists
            if all(isinstance(item, str) for item in alias_list):
                return [alias.lower() for alias in alias_list]
            elif all(isinstance(item, list) for item in alias_list):
                lower_mapped = []
                for sublist in alias_list:
                    lower_mapped.append([alias.lower() for alias in sublist])
                return lower_mapped

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
            for alias in map_lower(self._aliases[property_name]):
                if alias in lower_cols:
                    return col_dict[alias]
        
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
                logging.debug(f"Field mapping: '{prop}' -> '{match}'")
            else:
                # If no match found, use the first alias as fallback.
                # Required-field failures are surfaced by the required_fields check in __init__.
                if self._aliases[prop]:
                    fallback = self._aliases[prop][0]
                    discovered[prop] = fallback
                    logging.debug(
                        f"No column match found for '{prop}'; using fallback '{fallback}'. "
                        f"Tried aliases: {self._aliases[prop]}"
                    )
                else:
                    missing_input_fields.append(prop)

        # Warn if any input fields are missing and have no aliases
        if missing_input_fields:
            logging.warning(f"Input fields not found in DataFrame and have no aliases: {missing_input_fields}")
        
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

    def get_missing_required_fields(self, df: pd.DataFrame, required_fields: List[str]) -> List[str]:
        """Return error strings for any required fields not resolved to actual DataFrame columns."""
        missing = []
        for field in required_fields:
            resolved = self._values.get(field)
            if resolved not in df.columns:
                tried = self._aliases.get(field, [field])
                missing.append(f"'{field}': tried aliases {tried}")
        return missing

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
