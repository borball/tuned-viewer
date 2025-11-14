"""
Profile parser for tuned configuration files.

Handles parsing of tuned.conf files in INI format with support for:
- Variable expansion
- Include directives
- Section-based configuration
"""

import os
import re
from collections import OrderedDict
from configparser import ConfigParser
from typing import Dict, List, Optional, Tuple, Any


class TunedProfile:
    """Represents a parsed tuned profile."""

    def __init__(self, name: str):
        self.name = name
        self.variables = OrderedDict()
        self.units = OrderedDict()
        self.options = {}
        self.includes = []

    def __repr__(self):
        return f"TunedProfile(name='{self.name}', units={list(self.units.keys())})"


class TunedUnit:
    """Represents a configuration unit within a tuned profile."""

    def __init__(self, name: str, options: Dict[str, Any]):
        self.name = name
        self.options = options
        self.replace = options.pop('replace', '').lower() in ('true', '1', 'yes')
        self.priority = self._parse_priority(options.get('priority'))
        self.enabled = options.get('enabled', 'true').lower() in ('true', '1', 'yes')
        self.devices = options.get('devices', '')

    def _parse_priority(self, priority_str: Optional[str]) -> Optional[int]:
        """Parse priority value from string."""
        if priority_str is None:
            return None
        try:
            return int(priority_str)
        except (ValueError, TypeError):
            return None

    def __repr__(self):
        return f"TunedUnit(name='{self.name}', options={len(self.options)})"


class ProfileParser:
    """Parser for tuned profile configuration files."""

    MAIN_SECTION = 'main'
    VARIABLES_SECTION = 'variables'

    def __init__(self):
        self.variable_pattern = re.compile(r'\$\{([^}]+)\}')

    def parse_file(self, file_path: str) -> TunedProfile:
        """Parse a tuned profile configuration file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Profile file not found: {file_path}")

        profile_name = os.path.basename(os.path.dirname(file_path))
        profile = TunedProfile(profile_name)

        config = self._load_config(file_path)
        self._parse_main_section(config, profile)
        self._parse_variables_section(config, profile)
        self._parse_unit_sections(config, profile)

        return profile

    def _load_config(self, file_path: str) -> ConfigParser:
        """Load configuration file using ConfigParser."""
        config = ConfigParser(
            delimiters=('=',),
            inline_comment_prefixes=('#',),
            strict=False,
            interpolation=None  # Disable interpolation to handle variables manually
        )
        config.optionxform = str  # Preserve case sensitivity

        with open(file_path, 'r', encoding='utf-8') as f:
            config.read_file(f)

        return config

    def _parse_main_section(self, config: ConfigParser, profile: TunedProfile):
        """Parse the [main] section for profile options and includes."""
        if not config.has_section(self.MAIN_SECTION):
            return

        for key, value in config.items(self.MAIN_SECTION):
            if key == 'include':
                # Parse include directive - can be comma or semicolon separated
                includes = re.split(r'\s*[,;]\s*', value.strip())
                profile.includes.extend([inc.strip() for inc in includes if inc.strip()])
            else:
                profile.options[key] = value

    def _parse_variables_section(self, config: ConfigParser, profile: TunedProfile):
        """Parse the [variables] section."""
        if not config.has_section(self.VARIABLES_SECTION):
            return

        for key, value in config.items(self.VARIABLES_SECTION):
            profile.variables[key] = value

    def _parse_unit_sections(self, config: ConfigParser, profile: TunedProfile):
        """Parse all sections except main and variables as units."""
        for section_name in config.sections():
            if section_name in (self.MAIN_SECTION, self.VARIABLES_SECTION):
                continue

            options = dict(config.items(section_name))
            unit = TunedUnit(section_name, options)
            profile.units[section_name] = unit

    def expand_variables(self, text: str, variables: Dict[str, str]) -> str:
        """Expand variables in text using ${variable} syntax."""
        if not text:
            return text

        def replace_var(match):
            var_name = match.group(1)
            # Handle complex variable expressions like f:function:arg
            if ':' in var_name:
                # For now, just return the original - complex functions need special handling
                return match.group(0)
            return variables.get(var_name, match.group(0))

        return self.variable_pattern.sub(replace_var, text)

    def validate_profile_name(self, name: str) -> bool:
        """Validate profile name using tuned's naming rules."""
        pattern = r'^[a-zA-Z0-9_.-]+$'
        return bool(re.match(pattern, name))