"""Core process automation functionality.

Contains the canonical PIR, adapters, simulation, and AI components.
"""

from .pir import PIR, PIRBuilder, validate
from .scenario import Scenario, create_default_scenario

__all__ = ["PIR", "PIRBuilder", "validate", "Scenario", "create_default_scenario"]