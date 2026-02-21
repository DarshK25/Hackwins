"""
Feature Flags - single source of truth.

This module re-exports the canonical FeatureFlags defined in `app.features`
so existing imports from `app.config.features` continue to work.
"""

from app.features import FeatureFlags, feature_flags
