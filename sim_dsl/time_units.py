"""Simple time unit constants and helpers."""
from dataclasses import dataclass

HOURS = 1.0
MINUTES = 1.0 / 60.0
SECONDS = 1.0 / 3600.0


def to_hours(value: float, unit: float) -> float:
    """Convert a time value given its unit multiplier to hours."""
    return value * unit
