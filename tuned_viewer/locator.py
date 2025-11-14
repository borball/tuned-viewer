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

    def __init__(self, custom_directories: Optional[List[str]] = None):
        """Initialize with optional custom directories."""
        self.directories = custom_directories or self.STANDARD_DIRECTORIES.copy()

        # Add current directory profiles for testing
        if os.path.exists('./profiles'):
            self.directories.insert(0, './profiles')

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
        active_profile_file = '/etc/tuned/active_profile'

        if os.path.isfile(active_profile_file):
            try:
                with open(active_profile_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except (IOError, UnicodeDecodeError):
                pass

        return None

    def validate_directories(self) -> Dict[str, bool]:
        """Validate that profile directories exist and are accessible."""
        validation = {}

        for directory in self.directories:
            validation[directory] = os.path.isdir(directory) and os.access(directory, os.R_OK)

        return validation