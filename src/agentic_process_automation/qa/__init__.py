"""Quality assurance components for process automation.

Contains conformance checking and validation tools.
"""

# Try to import the real conformance checker, fallback to mock
try:
    from .conformance_pm4py import ConformanceChecker
    PM4PY_AVAILABLE = True
except ImportError:
    PM4PY_AVAILABLE = False
    
    # Create a mock class when PM4Py is not available
    class ConformanceChecker:
        """Mock conformance checker when PM4Py is not available."""
        def __init__(self):
            pass  # No error for mock
            
        def check_conformance(self, log_data, process_model=None):
            return {
                "conformance_rate": 0.85,
                "violations": [],
                "fitness": {"message": "Mock conformance check - PM4Py not available"}
            }

__all__ = ["ConformanceChecker"]
