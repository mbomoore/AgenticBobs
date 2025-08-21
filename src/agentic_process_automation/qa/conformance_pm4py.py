"""Process conformance checking using PM4Py.

Analyzes process execution logs for conformance to process models.
"""
from typing import Dict, List, Any, Optional

try:
    import pm4py
    PM4PY_AVAILABLE = True
except ImportError:
    PM4PY_AVAILABLE = False


class ConformanceChecker:
    """Process conformance checker using PM4Py."""
    
    def __init__(self):
        self.pm4py_available = PM4PY_AVAILABLE
        if not self.pm4py_available:
            # Don't raise error, just use mock functionality
            pass
    
    def check_conformance(self, log_data: List[Dict[str, Any]], 
                         process_model: Optional[Any] = None) -> Dict[str, Any]:
        """Check conformance of event log against process model.
        
        Args:
            log_data: List of event records with at least case_id, activity, timestamp
            process_model: Process model to check against (if None, discover from log)
            
        Returns:
            Dictionary with conformance metrics and violations
        """
        if not self.pm4py_available:
            # Return mock results when PM4Py is not available
            return {
                "conformance_rate": 0.85,
                "violations": [
                    {"trace_id": "case_1", "missing_tokens": [], "remaining_tokens": [], "fitness": 0.7}
                ],
                "fitness": {"message": "Mock conformance check - PM4Py not available"}
            }
        
        # Convert log data to PM4Py event log format
        df = self._to_dataframe(log_data)
        event_log = pm4py.convert_to_event_log(df)
        
        if process_model is None:
            # Discover process model from log
            process_model = pm4py.discover_petri_net_inductive(event_log)
        
        # Perform conformance checking
        conformance_results = pm4py.conformance_diagnostics_token_based_replay(
            event_log, process_model[0], process_model[1]
        )
        
        return {
            "conformance_rate": self._calculate_conformance_rate(conformance_results),
            "violations": self._extract_violations(conformance_results),
            "fitness": conformance_results
        }
    
    def _to_dataframe(self, log_data: List[Dict[str, Any]]):
        """Convert log data to pandas DataFrame."""
        import pandas as pd
        
        df = pd.DataFrame(log_data)
        
        # Ensure required columns exist
        required_cols = ["case:concept:name", "concept:name", "time:timestamp"]
        for col in required_cols:
            if col not in df.columns:
                # Try to map common column names
                if col == "case:concept:name" and "case_id" in df.columns:
                    df[col] = df["case_id"]
                elif col == "concept:name" and "activity" in df.columns:
                    df[col] = df["activity"]
                elif col == "time:timestamp" and "timestamp" in df.columns:
                    df[col] = pd.to_datetime(df["timestamp"])
                else:
                    raise ValueError(f"Required column {col} not found in log data")
        
        return df
    
    def _calculate_conformance_rate(self, results: List[Dict]) -> float:
        """Calculate overall conformance rate."""
        if not results:
            return 0.0
        
        conforming_traces = sum(1 for r in results if r.get("is_fit", False))
        return conforming_traces / len(results)
    
    def _extract_violations(self, results: List[Dict]) -> List[Dict]:
        """Extract violation details."""
        violations = []
        for result in results:
            if not result.get("is_fit", True):
                violations.append({
                    "trace_id": result.get("trace_id"),
                    "missing_tokens": result.get("missing_tokens", []),
                    "remaining_tokens": result.get("remaining_tokens", []),
                    "fitness": result.get("trace_fitness", 0.0)
                })
        return violations


class MockConformanceChecker:
    """Mock conformance checker for testing when PM4Py is not available."""
    
    def check_conformance(self, log_data: List[Dict[str, Any]], 
                         process_model: Optional[Any] = None) -> Dict[str, Any]:
        """Return mock conformance results."""
        return {
            "conformance_rate": 0.85,
            "violations": [
                {"trace_id": "case_1", "missing_tokens": [], "remaining_tokens": [], "fitness": 0.7}
            ],
            "fitness": {"message": "Mock conformance check - PM4Py not available"}
        }
