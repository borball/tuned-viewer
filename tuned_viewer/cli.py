"""
Command-line interface for the tuned profile viewer.

Provides commands to analyze, merge, and display tuned profiles.
"""

import argparse
import json
import sys
from typing import Optional, Dict, Any

from .locator import ProfileLocator
from .resolver import IncludeResolver, CircularIncludeError, ProfileNotFoundError
from .merger import ProfileMerger
from .parser import TunedProfile


class TunedViewer:
    """Main application class for the tuned profile viewer."""

    def __init__(self, custom_directories: Optional[list] = None):
        self.locator = ProfileLocator(custom_directories)
        self.resolver = IncludeResolver(self.locator)
        self.merger = ProfileMerger()

    def show_merged_profile(self, profile_name: str, output_format: str = 'ini') -> bool:
        """Show the final merged profile configuration."""
        try:
            profiles = self.resolver.resolve_hierarchy(profile_name)
            merged = self.merger.merge_profiles(profiles)

            if output_format == 'json':
                self._output_json(merged, profiles)
            elif output_format == 'summary':
                self._output_summary(merged, profiles)
            else:
                self._output_ini(merged)

            return True

        except (CircularIncludeError, ProfileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return False

    def show_hierarchy(self, profile_name: str) -> bool:
        """Show the profile hierarchy and dependencies."""
        try:
            tree = self.resolver.get_dependency_tree(profile_name)

            if 'error' in tree:
                print(f"Error: {tree['error']}", file=sys.stderr)
                return False

            self._output_hierarchy(tree)
            return True

        except Exception as e:
            print(f"Error analyzing hierarchy: {e}", file=sys.stderr)
            return False

    def list_profiles(self) -> bool:
        """List all available profiles."""
        try:
            profiles = self.locator.list_available_profiles()

            if not profiles:
                print("No tuned profiles found.")
                return True

            active_profile = self.locator.get_active_profile()

            print(f"Available tuned profiles ({len(profiles)} found):")
            print("-" * 50)

            for profile in profiles:
                info = self.locator.get_profile_info(profile)
                if not info:
                    continue

                marker = " *" if profile == active_profile else "  "
                summary = info.get('summary', 'No description available')
                source = info.get('source', 'unknown')

                print(f"{marker} {profile:<25} [{source}]")
                print(f"    {summary}")

            if active_profile:
                print(f"\n* Currently active: {active_profile}")

            return True

        except Exception as e:
            print(f"Error listing profiles: {e}", file=sys.stderr)
            return False

    def validate_profile(self, profile_name: str) -> bool:
        """Validate a profile and its hierarchy."""
        try:
            validation = self.resolver.validate_hierarchy(profile_name)

            print(f"Validation for profile '{profile_name}':")
            print("-" * 50)

            if validation['valid']:
                print("✓ Profile hierarchy is valid")
                print(f"✓ Found {validation['profile_count']} profile(s) in hierarchy")
                print(f"✓ Dependency chain: {' -> '.join(validation['profiles'])}")
            else:
                print("✗ Profile hierarchy has errors:")
                for error in validation['errors']:
                    print(f"  - {error}")

            if validation['warnings']:
                print("\nWarnings:")
                for warning in validation['warnings']:
                    print(f"  - {warning}")

            return validation['valid']

        except Exception as e:
            print(f"Error during validation: {e}", file=sys.stderr)
            return False

    def _output_ini(self, profile: TunedProfile):
        """Output profile in INI format."""
        print(f"# Merged tuned profile: {profile.name}")
        print(f"# This is the final configuration that would be applied")
        print()

        # Main section
        if profile.options:
            print("[main]")
            for key, value in profile.options.items():
                print(f"{key}={value}")
            print()

        # Variables section
        if profile.variables:
            print("[variables]")
            for key, value in profile.variables.items():
                print(f"{key}={value}")
            print()

        # Unit sections
        for unit_name, unit in profile.units.items():
            print(f"[{unit_name}]")

            # Add metadata comments
            if unit.priority is not None:
                print(f"# Priority: {unit.priority}")
            if not unit.enabled:
                print(f"# Enabled: {unit.enabled}")
            if unit.devices:
                print(f"# Devices: {unit.devices}")

            for key, value in unit.options.items():
                print(f"{key}={value}")
            print()

    def _output_json(self, merged: TunedProfile, profiles: list):
        """Output profile and hierarchy in JSON format."""
        data = {
            'merged_profile': {
                'name': merged.name,
                'variables': dict(merged.variables),
                'options': merged.options,
                'units': {}
            },
            'hierarchy': [p.name for p in profiles],
            'merge_summary': self.merger.get_merge_summary(profiles)
        }

        # Add unit details
        for unit_name, unit in merged.units.items():
            data['merged_profile']['units'][unit_name] = {
                'enabled': unit.enabled,
                'priority': unit.priority,
                'devices': unit.devices,
                'options': unit.options
            }

        print(json.dumps(data, indent=2))

    def _output_summary(self, merged: TunedProfile, profiles: list):
        """Output a human-readable summary."""
        print(f"Merged Profile Summary: {merged.name}")
        print("=" * 50)

        summary = self.merger.get_merge_summary(profiles)

        print(f"Profile hierarchy: {' -> '.join(summary['profiles'])}")
        print(f"Total sections: {summary['final_section_count']}")
        print(f"Total variables: {summary['final_variable_count']}")
        print(f"Conflicts resolved: {summary['conflicts_resolved']}")
        print()

        if merged.variables:
            print("Variables:")
            for key, value in merged.variables.items():
                print(f"  {key} = {value}")
            print()

        print("Configuration sections:")
        for unit_name, unit in merged.units.items():
            status = "enabled" if unit.enabled else "disabled"
            priority_info = f" (priority: {unit.priority})" if unit.priority is not None else ""
            print(f"  [{unit_name}] - {status}{priority_info}")

    def _output_hierarchy(self, tree: Dict):
        """Output the dependency tree."""
        print(f"Profile hierarchy for: {tree['root']}")
        print("=" * 50)
        print(f"Total profiles in hierarchy: {tree['total_count']}")
        print()

        for i, profile_info in enumerate(tree['profiles']):
            indent = "  " * i
            print(f"{indent}├─ {profile_info['name']}")

            if profile_info['includes']:
                print(f"{indent}│  Includes: {', '.join(profile_info['includes'])}")

            if profile_info['sections']:
                section_count = len(profile_info['sections'])
                print(f"{indent}│  Sections: {section_count} ({', '.join(profile_info['sections'][:3])}{'...' if section_count > 3 else ''})")

            if profile_info['variables']:
                var_count = len(profile_info['variables'])
                print(f"{indent}│  Variables: {var_count}")

            if i < len(tree['profiles']) - 1:
                print(f"{indent}│")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Tuned Profile Viewer - Analyze and merge tuned profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tuned-viewer list                           # List all available profiles
  tuned-viewer show balanced                  # Show merged balanced profile
  tuned-viewer show balanced --format json   # Show profile in JSON format
  tuned-viewer hierarchy latency-performance # Show profile hierarchy
  tuned-viewer validate realtime-virtual-host # Validate profile
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List available profiles')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show merged profile configuration')
    show_parser.add_argument('profile', help='Profile name to show')
    show_parser.add_argument('--format', choices=['ini', 'json', 'summary'], default='ini',
                            help='Output format (default: ini)')

    # Hierarchy command
    hierarchy_parser = subparsers.add_parser('hierarchy', help='Show profile hierarchy')
    hierarchy_parser.add_argument('profile', help='Profile name to analyze')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate profile hierarchy')
    validate_parser.add_argument('profile', help='Profile name to validate')

    # Global options
    parser.add_argument('--directories', nargs='+',
                       help='Custom directories to search for profiles')

    args = parser.parse_args()

    # Create viewer instance
    viewer = TunedViewer(args.directories)

    # Handle commands
    if args.command == 'list':
        success = viewer.list_profiles()
    elif args.command == 'show':
        success = viewer.show_merged_profile(args.profile, args.format)
    elif args.command == 'hierarchy':
        success = viewer.show_hierarchy(args.profile)
    elif args.command == 'validate':
        success = viewer.validate_profile(args.profile)
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())