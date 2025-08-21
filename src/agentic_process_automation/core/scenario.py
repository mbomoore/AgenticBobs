"""Scenario management for process simulation.

Provides configuration and management for simulation scenarios.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import uuid


@dataclass
class Scenario:
    """Configuration for a simulation scenario."""
    name: str
    description: str = ""
    duration: float = 24.0  # hours
    num_instances: int = 100
    arrival_rate: float = 1.0  # instances per hour
    resources: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.name:
            self.name = f"scenario_{str(uuid.uuid4())[:8]}"


def create_default_scenario(name: str = "default") -> Scenario:
    """Create a default simulation scenario."""
    return Scenario(
        name=name,
        description="Default simulation scenario",
        duration=24.0,
        num_instances=100,
        arrival_rate=1.0,
        resources={
            "default_resource": {
                "capacity": 1,
                "cost_per_hour": 50.0
            }
        },
        parameters={
            "random_seed": 42,
            "warm_up_time": 0.0
        }
    )
