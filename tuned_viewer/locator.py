"""
Profile locator for finding tuned profiles in standard directories.

Handles profile discovery and location using tuned's standard directory structure.
"""

import os
import glob
from typing import List, Optional, Dict


class ProfileLocator:
    """Locates tuned profiles in standard directories."""

    # Standard tuned profile directories in order of precedence
    STANDARD_DIRECTORIES = [
        '/etc/tuned/profiles',      # User-defined profiles (highest precedence)
        '/usr/lib/tuned/profiles',  # System profiles
        '/run/tuned/profiles',      # Runtime profiles
    ]

    # Pod-mounted directories (for OpenShift/Kubernetes environments)
    POD_MOUNT_DIRECTORIES = [
        '/host/etc/tuned/profiles',    # Host /etc mounted in pod
        '/host/usr/lib/tuned/profiles', # Host /usr/lib mounted in pod
        '/etc/tuned/profiles',         # Pod's own /etc
        '/usr/lib/tuned/profiles',     # Pod's own /usr/lib
    ]

    def __init__(self, custom_directories: Optional[List[str]] = None, detect_pod_env: bool = True):
        """Initialize with optional custom directories."""
        self.in_pod = self._detect_pod_environment() if detect_pod_env else False

        if custom_directories:
            self.directories = custom_directories
        elif self.in_pod:
            # Use pod-aware directories when running in a container
            self.directories = self.POD_MOUNT_DIRECTORIES.copy()
        else:
            self.directories = self.STANDARD_DIRECTORIES.copy()

        # Add current directory profiles for testing
        if os.path.exists('./profiles'):
            self.directories.insert(0, './profiles')

    def _detect_pod_environment(self) -> bool:
        """Detect if we're running inside a Kubernetes pod."""
        return (
            os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount') or
            os.environ.get('KUBERNETES_SERVICE_HOST') is not None or
            os.path.exists('/host/etc') or  # Common host mount point
            os.environ.get('NODE_NAME') is not None  # Often set in tuned pods
        )

    def find_profile(self, profile_name: str) -> Optional[str]:
        """Find a profile configuration file by name."""
        if not profile_name:
            return None

        for directory in self.directories:
            if not os.path.isdir(directory):
                continue

            profile_path = os.path.join(directory, profile_name, 'tuned.conf')
            if os.path.isfile(profile_path):
                return profile_path

        return None

    def list_available_profiles(self) -> List[str]:
        """List all available profile names."""
        profiles = set()

        for directory in self.directories:
            if not os.path.isdir(directory):
                continue

            # Find all subdirectories with tuned.conf files
            pattern = os.path.join(directory, '*', 'tuned.conf')
            for conf_file in glob.glob(pattern):
                profile_name = os.path.basename(os.path.dirname(conf_file))
                profiles.add(profile_name)

        return sorted(list(profiles))

    def get_profile_info(self, profile_name: str) -> Optional[Dict[str, str]]:
        """Get basic information about a profile."""
        profile_path = self.find_profile(profile_name)
        if not profile_path:
            return None

        profile_dir = os.path.dirname(profile_path)

        info = {
            'name': profile_name,
            'path': profile_path,
            'directory': profile_dir,
            'source': self._get_source_type(profile_dir)
        }

        # Try to read summary from the profile
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('summary='):
                        info['summary'] = line.split('=', 1)[1].strip()
                        break
        except (IOError, UnicodeDecodeError):
            pass

        return info

    def _get_source_type(self, profile_dir: str) -> str:
        """Determine the source type of a profile based on its directory."""
        if '/etc/tuned/profiles' in profile_dir:
            return 'user'
        elif '/usr/lib/tuned/profiles' in profile_dir:
            return 'system'
        elif '/run/tuned/profiles' in profile_dir:
            return 'runtime'
        else:
            return 'custom'

    def get_active_profile(self) -> Optional[str]:
        """Get the currently active profile name from /etc/tuned/active_profile."""
        # Try different locations based on environment
        active_profile_candidates = [
            '/etc/tuned/active_profile',      # Standard location
            '/host/etc/tuned/active_profile', # Host mount in pod
        ]

        for active_profile_file in active_profile_candidates:
            if os.path.isfile(active_profile_file):
                try:
                    with open(active_profile_file, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                except (IOError, UnicodeDecodeError):
                    continue

        return None

    def get_environment_info(self) -> Dict[str, any]:
        """Get information about the current environment."""
        info = {
            'in_pod': self.in_pod,
            'searched_directories': self.directories,
            'environment_variables': {}
        }

        # Gather relevant environment variables
        env_vars = ['NODE_NAME', 'KUBERNETES_SERVICE_HOST', 'KUBERNETES_NAMESPACE', 'POD_NAME']
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                info['environment_variables'][var] = value

        # Check for service account
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
            info['service_account'] = True
            # Try to read namespace
            try:
                with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as f:
                    info['namespace'] = f.read().strip()
            except (IOError, UnicodeDecodeError):
                pass

        return info

    def validate_directories(self) -> Dict[str, bool]:
        """Validate that profile directories exist and are accessible."""
        validation = {}

        for directory in self.directories:
            validation[directory] = os.path.isdir(directory) and os.access(directory, os.R_OK)

        return validation