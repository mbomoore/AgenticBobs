"""Stochastic utilities for process simulation.

Provides random distributions and stochastic process modeling.
"""
import random
from typing import Callable, Any
from abc import ABC, abstractmethod


class Distribution(ABC):
    """Abstract base class for probability distributions."""
    
    @abstractmethod
    def sample(self) -> float:
        """Generate a random sample from this distribution."""
        pass


class ConstantDistribution(Distribution):
    """Constant (deterministic) distribution."""
    
    def __init__(self, value: float):
        self.value = value
    
    def sample(self) -> float:
        return self.value


class UniformDistribution(Distribution):
    """Uniform distribution between min and max values."""
    
    def __init__(self, min_val: float, max_val: float):
        self.min_val = min_val
        self.max_val = max_val
    
    def sample(self) -> float:
        return random.uniform(self.min_val, self.max_val)


class NormalDistribution(Distribution):
    """Normal (Gaussian) distribution."""
    
    def __init__(self, mean: float, std_dev: float):
        self.mean = mean
        self.std_dev = std_dev
    
    def sample(self) -> float:
        return random.normalvariate(self.mean, self.std_dev)


class ExponentialDistribution(Distribution):
    """Exponential distribution (commonly used for arrival times)."""
    
    def __init__(self, rate: float):
        self.rate = rate
    
    def sample(self) -> float:
        return random.expovariate(self.rate)


class TriangularDistribution(Distribution):
    """Triangular distribution."""
    
    def __init__(self, low: float, high: float, mode: float):
        self.low = low
        self.high = high
        self.mode = mode
    
    def sample(self) -> float:
        return random.triangular(self.low, self.high, self.mode)


def create_distribution(dist_type: str, **params) -> Distribution:
    """Factory function to create distributions by name."""
    distributions = {
        "constant": ConstantDistribution,
        "uniform": UniformDistribution,
        "normal": NormalDistribution,
        "exponential": ExponentialDistribution,
        "triangular": TriangularDistribution
    }
    
    if dist_type not in distributions:
        raise ValueError(f"Unknown distribution type: {dist_type}")
    
    return distributions[dist_type](**params)


# Common distribution instances
ZERO = ConstantDistribution(0.0)
ONE = ConstantDistribution(1.0)
UNIT_UNIFORM = UniformDistribution(0.0, 1.0)
STANDARD_NORMAL = NormalDistribution(0.0, 1.0)
