"""
Configuration package for AI Gateway.

Note: The canonical settings live in app/config.py (one level up).
This package exists for organizing feature flags and sub-config.

Exposes:
- settings: main application settings
- feature_flags: feature flag configuration
"""

import sys
import os

# Ensure the parent package's config.py (app/config.py) is importable
# by importing it directly before this package shadows it.
# We use importlib to load the sibling file config.py as a module.
import importlib.util as _ilu

_config_file = os.path.join(os.path.dirname(__file__), "..", "config.py")
_spec = _ilu.spec_from_file_location("_app_config_module", _config_file)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Settings = _mod.Settings
settings = _mod.settings
get_settings = _mod.get_settings

from .features import feature_flags, FeatureFlags  # noqa: F401
