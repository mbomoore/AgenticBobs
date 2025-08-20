"""Quality assurance components for process automation.

Contains conformance checking and validation tools.
"""

from .conformance_pm4py import ConformanceChecker, MockConformanceChecker

__all__ = ["ConformanceChecker", "MockConformanceChecker"]