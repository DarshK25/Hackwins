"""
Configuration package for AI Gateway.

Exposes:
- settings: main application settings
- feature_flags: feature flag configuration
"""

from .config import settings, Settings  # noqa: F401
from .features import feature_flags, FeatureFlags  # noqa: F401

