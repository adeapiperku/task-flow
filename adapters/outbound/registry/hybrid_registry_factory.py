# adapters/outbound/registry/hybrid_registry_factory.py
"""
Factory for creating hybrid job registries that combine plugin and DB sources.

NOTE: This file is deprecated. Hybrid registries are now created directly
in dispatch_job() using UoW session management. See worker/runner.py.
"""
from __future__ import annotations

# This file is kept for reference but hybrid registries should be created
# in dispatch_job() with proper UoW session management.
# See worker/runner.py:dispatch_job() for the correct implementation.

