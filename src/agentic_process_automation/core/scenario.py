"""Scenario management for process simulation.

Defines scenarios for simulation runs with parameters and configurations.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Scenario:
    """Represents a simulation scenario with parameters and configuration."""
    
    name: str
    horizon: float = 1000.0  # simulation time horizon
    seed: int = 42  # random seed
    demand_params: Dict[str, Any] = field(default_factory=dict)  # demand generation parameters
    resource_params: Dict[str, Any] = field(default_factory=dict)  # resource configuration
    policy_params: Dict[str, Any] = field(default_factory=dict)  # policy parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary for serialization."""
        return {
            "name": self.name,
            "horizon": self.horizon,
            "seed": self.seed,
            "demand_params": self.demand_params,
            "resource_params": self.resource_params,
            "policy_params": self.policy_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scenario":
        """Create scenario from dictionary."""
        return cls(
            name=data["name"],
            horizon=data.get("horizon", 1000.0),
            seed=data.get("seed", 42),
            demand_params=data.get("demand_params", {}),
            resource_params=data.get("resource_params", {}),
            policy_params=data.get("policy_params", {})
        )


def create_default_scenario(name: str = "default") -> Scenario:
    """Create a default scenario for testing."""
    return Scenario(
        name=name,
        horizon=100.0,
        seed=42,
        demand_params={"arrival_rate": 1.0},
        resource_params={"default_pool": {"size": 3, "skills": ["general"]}},
        policy_params={"queue_discipline": "FIFO"}
    )