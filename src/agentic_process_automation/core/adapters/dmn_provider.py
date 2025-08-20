"""DMN (Decision Model and Notation) provider interface.

Supports both REST-based and local DMN evaluation.
"""
import json
from typing import Dict, Any, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class DMNProvider:
    """Provider for DMN decision evaluation."""
    
    def __init__(self, mode: str = "rest", base_url: Optional[str] = None, 
                 model_id: Optional[str] = None, local_evaluator=None):
        """Initialize DMN provider.
        
        Args:
            mode: "rest" for REST API or "local" for local evaluation
            base_url: Base URL for REST API (required if mode="rest")
            model_id: Model ID for REST API (required if mode="rest")
            local_evaluator: Local evaluator instance (required if mode="local")
        """
        self.mode = mode
        self.base_url = base_url
        self.model_id = model_id
        self.local_evaluator = local_evaluator
        
        if mode == "rest" and not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for REST mode")
    
    def evaluate(self, decision_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a decision with given context.
        
        Args:
            decision_id: ID of the decision to evaluate
            context: Input context dictionary
            
        Returns:
            Decision result dictionary
        """
        if self.mode == "rest":
            if not self.base_url or not self.model_id:
                raise ValueError("base_url and model_id required for REST mode")
            
            url = f"{self.base_url}/dmn/decision/{self.model_id}/{decision_id}"
            response = requests.post(url, json=context, timeout=15)
            response.raise_for_status()
            return response.json()
            
        elif self.mode == "local":
            if not self.local_evaluator:
                raise ValueError("local_evaluator required for local mode")
            
            return self.local_evaluator.evaluate(decision_id, context)
            
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


class MockDMNProvider(DMNProvider):
    """Mock DMN provider for testing."""
    
    def __init__(self):
        super().__init__(mode="local")
        self.decisions = {}
    
    def add_decision(self, decision_id: str, result: Dict[str, Any]):
        """Add a mock decision result."""
        self.decisions[decision_id] = result
    
    def evaluate(self, decision_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock result or default."""
        return self.decisions.get(decision_id, {"result": "default"})