"""Core process automation logic.

Contains PIR, simulation, adapters, and core algorithms.
"""

# Core exports
from .pir import PIR, PIRBuilder, Node, Edge, validate

__all__ = [
    "PIR", "PIRBuilder", "Node", "Edge", "validate"
]
