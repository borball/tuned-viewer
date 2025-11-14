"""
Profile merger for combining tuned profiles according to tuned's merging rules.

Implements the same merging algorithm used by tuned itself.
"""

from functools import reduce
from collections import OrderedDict
from typing import List, Dict, Any
from .parser import TunedProfile, TunedUnit


class ProfileMerger:
    """Merges tuned profiles according to tuned's algorithm."""

    VARIABLES_SECTION = 'variables'
    SCRIPT_SECTION = 'script'

    def merge_profiles(self, profiles: List[TunedProfile]) -> TunedProfile:
        """
        Merge multiple profiles into a single profile.

        Profiles should be in dependency order (base profiles first).
        """
        if not profiles:
            return TunedProfile("empty")

        # Use reduce to merge profiles sequentially
        merged = reduce(self._merge_two, profiles, TunedProfile("base"))

        # Set the final name to the last profile's name
        if profiles:
            merged.name = profiles[-1].name

        return merged

    def _merge_two(self, profile_a: TunedProfile, profile_b: TunedProfile) -> TunedProfile:
        """Merge two profiles according to tuned's merging rules."""
        # If profile_a is empty (initial case), start with profile_b
        if not profile_a.name or profile_a.name == "base":
            result = TunedProfile(profile_b.name)
            result.variables.update(profile_b.variables)
            result.units.update(profile_b.units)
            result.options.update(profile_b.options)
            result.includes = profile_b.includes.copy()
            return result

        # Merge into profile_a
        result = TunedProfile(profile_a.name)
        result.variables = profile_a.variables.copy()
        result.units = OrderedDict()
        result.options = profile_a.options.copy()
        result.includes = profile_a.includes.copy()

        # Copy existing units
        for unit_name, unit in profile_a.units.items():
            result.units[unit_name] = self._copy_unit(unit)

        # Update options
        result.options.update(profile_b.options)

        # Merge variables
        self._merge_variables(result, profile_b)

        # Merge units
        self._merge_units(result, profile_b)

        return result

    def _merge_variables(self, target: TunedProfile, source: TunedProfile):
        """Merge variables from source into target."""
        if not source.variables:
            return

        # Check if variables unit has replace=true
        variables_unit = source.units.get(self.VARIABLES_SECTION)
        if variables_unit and variables_unit.replace:
            target.variables.clear()

        # Update variables
        for key, value in source.variables.items():
            if key not in target.variables:
                # New variable - add at beginning (prepend)
                target.variables[key] = value
                target.variables.move_to_end(key, last=False)
            else:
                # Existing variable - update value
                target.variables[key] = value

    def _merge_units(self, target: TunedProfile, source: TunedProfile):
        """Merge units from source into target."""
        for unit_name, source_unit in source.units.items():
            if unit_name == self.VARIABLES_SECTION:
                continue  # Variables handled separately

            if source_unit.replace or unit_name not in target.units:
                # Replace existing unit or add new unit
                target.units[unit_name] = self._copy_unit(source_unit)
            else:
                # Merge with existing unit
                target_unit = target.units[unit_name]
                self._merge_unit_options(target_unit, source_unit)

    def _merge_unit_options(self, target_unit: TunedUnit, source_unit: TunedUnit):
        """Merge options from source unit into target unit."""
        # Handle script concatenation
        if target_unit.name == self.SCRIPT_SECTION and 'script' in source_unit.options:
            existing_script = target_unit.options.get('script', '')
            new_script = source_unit.options['script']
            target_unit.options['script'] = existing_script + new_script

        # Update other options
        for key, value in source_unit.options.items():
            if key == 'script' and target_unit.name == self.SCRIPT_SECTION:
                continue  # Already handled above

            # Handle drop options (remove specific options)
            if key.startswith('drop_'):
                option_to_drop = key[5:]  # Remove 'drop_' prefix
                target_unit.options.pop(option_to_drop, None)
                continue

            target_unit.options[key] = value

        # Update unit properties if specified
        if source_unit.priority is not None:
            target_unit.priority = source_unit.priority

        if 'enabled' in source_unit.options:
            target_unit.enabled = source_unit.options['enabled'].lower() in ('true', '1', 'yes')

        if 'devices' in source_unit.options:
            target_unit.devices = source_unit.options['devices']

    def _copy_unit(self, unit: TunedUnit) -> TunedUnit:
        """Create a deep copy of a unit."""
        new_unit = TunedUnit(unit.name, unit.options.copy())
        new_unit.replace = unit.replace
        new_unit.priority = unit.priority
        new_unit.enabled = unit.enabled
        new_unit.devices = unit.devices
        return new_unit

    def get_merge_summary(self, profiles: List[TunedProfile]) -> Dict[str, Any]:
        """Get a summary of what would be merged."""
        if not profiles:
            return {'profiles': [], 'total_sections': 0, 'final_sections': []}

        merged = self.merge_profiles(profiles)

        summary = {
            'profiles': [p.name for p in profiles],
            'merge_order': [p.name for p in profiles],
            'total_input_sections': sum(len(p.units) for p in profiles),
            'final_sections': list(merged.units.keys()),
            'final_section_count': len(merged.units),
            'final_variables': list(merged.variables.keys()),
            'final_variable_count': len(merged.variables),
            'conflicts_resolved': self._count_conflicts(profiles)
        }

        return summary

    def _count_conflicts(self, profiles: List[TunedProfile]) -> int:
        """Count how many section conflicts were resolved during merging."""
        all_sections = set()
        total_sections = 0

        for profile in profiles:
            total_sections += len(profile.units)
            all_sections.update(profile.units.keys())

        return total_sections - len(all_sections)