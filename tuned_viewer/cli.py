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
from .k8s_integration import OpenShiftTunedIntegration, PodAwareLocator


class TunedViewer:
    """Main application class for the tuned profile viewer."""

    def __init__(self, custom_directories: Optional[list] = None):
        self.locator = ProfileLocator(custom_directories)
        self.resolver = IncludeResolver(self.locator)
        self.merger = ProfileMerger()
        self.openshift = OpenShiftTunedIntegration()
        self.pod_locator = PodAwareLocator(self.openshift)

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

    def show_cluster_status(self) -> bool:
        """Show tuned status across the OpenShift cluster."""
        try:
            status = self.openshift.get_cluster_tuned_status()

            print("OpenShift Cluster Tuned Status")
            print("=" * 50)

            # Show pod status
            pods = status["pods"]
            print(f"Tuned Pods: {len(pods)}")
            print("-" * 30)

            for pod in pods:
                status_symbol = "✓" if pod["status"] == "Running" else "✗"
                restarts_info = f" (restarts: {pod['restarts']})" if pod["restarts"] > 0 else ""

                print(f"{status_symbol} {pod['name']:<20} | Node: {pod['node']:<15} | {pod['status']}{restarts_info}")

            # Show active profiles per node
            print(f"\nActive Profiles per Node:")
            print("-" * 30)

            active_profiles = status["active_profiles"]
            for node, info in active_profiles.items():
                profile = info.get("profile", "unknown")
                pod_status = info.get("status", "unknown")
                print(f"  {node:<20} | {profile:<15} | Pod: {info['pod']} ({pod_status})")

            # Show ConfigMaps
            configmaps = status["configmaps"]
            if configmaps:
                print(f"\nTuned ConfigMaps: {len(configmaps)}")
                print("-" * 30)
                for cm in configmaps:
                    print(f"  {cm['name']:<25} | Keys: {', '.join(cm['data_keys'][:3])}{'...' if len(cm['data_keys']) > 3 else ''}")

            # Show Custom Resources
            custom_resources = status["custom_resources"]
            if custom_resources:
                print(f"\nTuned Custom Resources: {len(custom_resources)}")
                print("-" * 30)
                for cr in custom_resources:
                    print(f"  {cr['name']}")

            return True

        except Exception as e:
            print(f"Error getting cluster status: {e}", file=sys.stderr)
            return False

    def sync_from_cluster(self, output_dir: str = "./cluster_profiles") -> bool:
        """Sync tuned profiles from cluster to local directory."""
        try:
            print(f"Syncing tuned profiles from cluster to: {output_dir}")
            print("-" * 50)

            results = self.pod_locator.sync_profiles_from_cluster(output_dir)

            # Report synced profiles from pods
            synced_pods = results["synced_pods"]
            if synced_pods:
                print(f"Synced {len(synced_pods)} profiles from pods:")
                for sync in synced_pods:
                    print(f"  ✓ {sync['profile']} from pod {sync['pod']} (node: {sync['node']})")
            else:
                print("  No profiles synced from pods")

            # Report synced ConfigMaps
            synced_cms = results["synced_configmaps"]
            if synced_cms:
                print(f"\nSynced {len(synced_cms)} ConfigMaps:")
                for cm in synced_cms:
                    print(f"  ✓ {cm}")
            else:
                print("\n  No profiles synced from ConfigMaps")

            # Report errors
            if results["errors"]:
                print(f"\nErrors encountered:")
                for error in results["errors"]:
                    print(f"  ✗ {error}")

            print(f"\nProfiles synced to: {output_dir}")
            print("You can now use 'tuned-viewer --directories {output_dir}' to analyze them")

            return True

        except Exception as e:
            print(f"Error syncing from cluster: {e}", file=sys.stderr)
            return False

    def show_environment_info(self) -> bool:
        """Show information about the current environment."""
        try:
            env_info = self.locator.get_environment_info()

            print("Environment Information")
            print("=" * 50)

            print(f"Running in pod: {'Yes' if env_info['in_pod'] else 'No'}")
            print(f"OpenShift node: {'Yes' if env_info.get('in_openshift_node') else 'No'}")

            if env_info.get('namespace'):
                print(f"Namespace: {env_info['namespace']}")

            # Show active profile if on OpenShift node
            if env_info.get('in_openshift_node'):
                try:
                    import subprocess
                    result = subprocess.run(['tuned-adm', 'active'], capture_output=True, text=True)
                    if result.returncode == 0:
                        active_line = [line for line in result.stdout.split('\n') if 'Current active profile:' in line]
                        if active_line:
                            active_profile = active_line[0].split(':')[-1].strip()
                            print(f"Active tuned profile: {active_profile}")
                except:
                    pass

            if env_info['environment_variables']:
                print("\nEnvironment Variables:")
                for var, value in env_info['environment_variables'].items():
                    print(f"  {var}: {value}")

            print(f"\nSearched Directories:")
            validation = self.locator.validate_directories()
            for directory in env_info['searched_directories']:
                accessible = validation.get(directory, False)
                symbol = "✓" if accessible else "✗"
                print(f"  {symbol} {directory}")

            active_profile = self.locator.get_active_profile()
            if active_profile:
                print(f"\nActive Profile: {active_profile}")

            return True

        except Exception as e:
            print(f"Error getting environment info: {e}", file=sys.stderr)
            return False

    def analyze_node_profile(self, node_name: str) -> bool:
        """Analyze the tuned profile for a specific node."""
        try:
            status = self.openshift.get_cluster_tuned_status()
            active_profiles = status["active_profiles"]

            if node_name not in active_profiles:
                available_nodes = list(active_profiles.keys())
                print(f"Node '{node_name}' not found. Available nodes: {', '.join(available_nodes)}", file=sys.stderr)
                return False

            node_info = active_profiles[node_name]
            profile_name = node_info["profile"]
            pod_name = node_info["pod"]

            print(f"Node Profile Analysis: {node_name}")
            print("=" * 50)
            print(f"Node: {node_name}")
            print(f"Pod: {pod_name}")
            print(f"Profile: {profile_name}")
            print()

            if not profile_name:
                print("No active profile found for this node")
                return False

            # Try to show the merged profile
            return self.show_merged_profile(profile_name)

        except Exception as e:
            print(f"Error analyzing node profile: {e}", file=sys.stderr)
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
  # Local profile analysis
  tuned-viewer list                           # List all available profiles
  tuned-viewer show balanced                  # Show merged balanced profile
  tuned-viewer show balanced --format json   # Show profile in JSON format
  tuned-viewer hierarchy latency-performance # Show profile hierarchy
  tuned-viewer validate realtime-virtual-host # Validate profile

  # OpenShift/Kubernetes cluster operations
  tuned-viewer cluster                        # Show cluster tuned status
  tuned-viewer sync                           # Sync profiles from cluster
  tuned-viewer env                            # Show environment info
  tuned-viewer node worker-1                 # Analyze profile for specific node
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

    # OpenShift/Kubernetes specific commands
    cluster_parser = subparsers.add_parser('cluster', help='Show OpenShift cluster tuned status')

    sync_parser = subparsers.add_parser('sync', help='Sync profiles from cluster')
    sync_parser.add_argument('--output-dir', default='./cluster_profiles',
                            help='Directory to sync profiles to (default: ./cluster_profiles)')

    env_parser = subparsers.add_parser('env', help='Show environment information')

    node_parser = subparsers.add_parser('node', help='Analyze tuned profile for a specific node')
    node_parser.add_argument('node_name', help='Node name to analyze')

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
    elif args.command == 'cluster':
        success = viewer.show_cluster_status()
    elif args.command == 'sync':
        success = viewer.sync_from_cluster(args.output_dir)
    elif args.command == 'env':
        success = viewer.show_environment_info()
    elif args.command == 'node':
        success = viewer.analyze_node_profile(args.node_name)
    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())