"""Stochastic utilities for process simulation.

Provides random number generation and distribution sampling.
"""
import random
import math
from typing import List, Union


class RNG:
    """Random number generator with various distribution methods."""
    
    def __init__(self, seed: int = None):
        self.r = random.Random(seed)
    
    def exp(self, rate: float) -> float:
        """Sample from exponential distribution."""
        return self.r.expovariate(rate)
    
    def lognormal(self, mu: float, sigma: float) -> float:
        """Sample from lognormal distribution."""
        return self.r.lognormvariate(mu, sigma)
    
    def empirical(self, samples: List[Union[int, float]]) -> Union[int, float]:
        """Sample from empirical distribution (uniform over provided samples)."""
        return self.r.choice(samples)
    
    def uniform(self, a: float, b: float) -> float:
        """Sample from uniform distribution."""
        return self.r.uniform(a, b)
    
    def normal(self, mu: float, sigma: float) -> float:
        """Sample from normal distribution."""
        return self.r.normalvariate(mu, sigma)
    
    def triangular(self, low: float, high: float, mode: float) -> float:
        """Sample from triangular distribution."""
        return self.r.triangular(low, high, mode)