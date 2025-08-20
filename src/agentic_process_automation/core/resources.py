"""Resources management for process automation.

Handles business calendars, resource pools, shifts, and availability.
"""
from datetime import datetime
from typing import Dict, List, Optional

try:
    from workalendar.usa import UnitedStates
    import holidays
    
    cal = UnitedStates()
    us_holidays = holidays.US()
    
    def is_business_time(dt: datetime) -> bool:
        return cal.is_working_day(dt.date()) and dt.date() not in us_holidays
        
except ImportError:
    # Fallback implementation if optional dependencies not available
    def is_business_time(dt: datetime) -> bool:
        # Simple fallback: Monday-Friday, no holiday checking
        return dt.weekday() < 5


def resource_available(pool_cfg: Dict, dt: datetime, skill: str) -> bool:
    """Check if a resource with given skill is available at the given time.
    
    Args:
        pool_cfg: Resource pool configuration dict with keys:
            - "size": int - number of resources
            - "skills": List[str] - available skills
            - "shifts": List[Dict] - shift definitions
        dt: datetime to check
        skill: required skill
        
    Returns:
        bool: True if resource is available
    """
    has_skill = skill in pool_cfg.get("skills", [])
    # TODO: check shift window + business time
    return has_skill and is_business_time(dt)


class ResourcePool:
    """Represents a pool of resources with skills and availability."""
    
    def __init__(self, name: str, size: int, skills: List[str], shifts: Optional[List[Dict]] = None):
        self.name = name
        self.size = size
        self.skills = skills
        self.shifts = shifts or []
    
    def is_available(self, dt: datetime, skill: str) -> bool:
        """Check if this pool can provide the required skill at the given time."""
        return resource_available({
            "size": self.size,
            "skills": self.skills,
            "shifts": self.shifts
        }, dt, skill)