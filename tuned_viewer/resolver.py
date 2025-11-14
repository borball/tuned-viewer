"""
Include resolver for handling tuned profile hierarchies.

Resolves include directives recursively to build complete profile dependency chains.
"""

import os
from typing import List, Set, Dict, Optional
from .parser import ProfileParser, TunedProfile
from .locator import ProfileLocator


class CircularIncludeError(Exception):
    """Raised when circular includes are detected."""
    pass


class ProfileNotFoundError(Exception):
    """Raised when a required profile cannot be found."""
    pass


class IncludeResolver:
    """Resolves profile include hierarchies."""

    def __init__(self, locator: Optional[ProfileLocator] = None):
        self.locator = locator or ProfileLocator()
        self.parser = ProfileParser()

    def resolve_hierarchy(self, profile_name: str) -> List[TunedProfile]:
        """
        Resolve the complete hierarchy for a profile.

        Returns profiles in dependency order (base profiles first).
        """
        processed_profiles = set()
        profile_chain = []

        self._resolve_recursive(profile_name, processed_profiles, profile_chain, [])

        return profile_chain

    def _resolve_recursive(
        self,
        profile_name: str,
        processed: Set[str],
        chain: List[TunedProfile],
        include_path: List[str]
    ):
        """Recursively resolve profile includes."""
        # Check for circular dependencies
        if profile_name in include_path:
            cycle = include_path[include_path.index(profile_name):] + [profile_name]
            raise CircularIncludeError(f"Circular include detected: {' -> '.join(cycle)}")

        # Skip if already processed
        if profile_name in processed:
            return

        # Find and parse the profile
        profile_path = self.locator.find_profile(profile_name)
        if not profile_path:
            searched_dirs = ', '.join(self.locator.directories)
            raise ProfileNotFoundError(
                f"Profile '{profile_name}' not found in directories: {searched_dirs}"
            )

        profile = self.parser.parse_file(profile_path)
        processed.add(profile_name)

        # Process includes first (dependency order)
        current_path = include_path + [profile_name]
        for include_name in profile.includes:
            # Handle external files (paths starting with /)
            if include_name.startswith('/'):
                include_profile = self._parse_external_include(include_name, profile_name)
                if include_profile:
                    chain.append(include_profile)
            else:
                # Regular profile include
                self._resolve_recursive(include_name, processed, chain, current_path)

        # Add current profile after its dependencies
        chain.append(profile)

    def _parse_external_include(self, include_path: str, profile_name: str) -> Optional[TunedProfile]:
        """Parse external include files (e.g., /etc/tuned/profile-variables.conf)."""
        if not os.path.isfile(include_path):
            # Don't raise error for missing external files - they're optional
            return None

        try:
            # Create a synthetic profile for the external include
            external_profile = TunedProfile(f"{profile_name}_external")

            # Use the parser's config loader but handle it as variables
            config = self.parser._load_config(include_path)

            # External includes are typically variable files
            if config.has_section('variables'):
                for key, value in config.items('variables'):
                    external_profile.variables[key] = value
            else:
                # If no variables section, treat the whole file as variables
                for section_name in config.sections():
                    for key, value in config.items(section_name):
                        external_profile.variables[f"{section_name}.{key}"] = value

            return external_profile

        except Exception:
            # Ignore errors in external includes
            return None

    def get_dependency_tree(self, profile_name: str) -> Dict:
        """
        Get a tree representation of profile dependencies.

        Returns a dictionary showing the hierarchical structure.
        """
        try:
            profiles = self.resolve_hierarchy(profile_name)
            return self._build_tree(profiles)
        except (CircularIncludeError, ProfileNotFoundError) as e:
            return {'error': str(e)}

    def _build_tree(self, profiles: List[TunedProfile]) -> Dict:
        """Build a tree structure from resolved profiles."""
        tree = {
            'root': profiles[-1].name if profiles else None,
            'profiles': [],
            'total_count': len(profiles)
        }

        for profile in profiles:
            profile_info = {
                'name': profile.name,
                'includes': profile.includes.copy(),
                'sections': list(profile.units.keys()),
                'variables': list(profile.variables.keys()),
                'options': profile.options.copy()
            }
            tree['profiles'].append(profile_info)

        return tree

    def validate_hierarchy(self, profile_name: str) -> Dict[str, any]:
        """
        Validate a profile hierarchy and return validation results.

        Checks for circular dependencies, missing profiles, and other issues.
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'profile_count': 0,
            'profiles': []
        }

        try:
            profiles = self.resolve_hierarchy(profile_name)
            validation['profile_count'] = len(profiles)
            validation['profiles'] = [p.name for p in profiles]

        except CircularIncludeError as e:
            validation['valid'] = False
            validation['errors'].append(f"Circular dependency: {str(e)}")

        except ProfileNotFoundError as e:
            validation['valid'] = False
            validation['errors'].append(f"Missing profile: {str(e)}")

        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Unexpected error: {str(e)}")

        return validation