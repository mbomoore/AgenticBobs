"""Resource management for process automation.

Handles business calendars, resource pools, and capacity management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, time, timedelta

try:
    from workalendar.usa import UnitedStates
    from holidays import UnitedStates as USHolidays
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False


@dataclass
class ResourcePool:
    """Represents a pool of resources with specific skills and capacity."""
    name: str
    capacity: int
    skills: List[str] = field(default_factory=list)
    cost_per_hour: float = 0.0
    availability_schedule: Optional[Dict[str, Any]] = None


@dataclass 
class BusinessCalendar:
    """Business calendar for resource availability."""
    name: str
    working_hours: Dict[str, List[tuple]] = field(default_factory=lambda: {
        "monday": [(time(9, 0), time(17, 0))],
        "tuesday": [(time(9, 0), time(17, 0))],
        "wednesday": [(time(9, 0), time(17, 0))],
        "thursday": [(time(9, 0), time(17, 0))],
        "friday": [(time(9, 0), time(17, 0))],
        "saturday": [],
        "sunday": []
    })
    holidays: List[datetime] = field(default_factory=list)
    timezone: str = "UTC"
    
    def is_working_day(self, date: datetime) -> bool:
        """Check if a given date is a working day."""
        # Check if it's a holiday
        if date.date() in [h.date() for h in self.holidays]:
            return False
        
        # Check if it's a working day of week
        day_name = date.strftime("%A").lower()
        return day_name in self.working_hours and len(self.working_hours[day_name]) > 0
    
    def get_working_hours(self, date: datetime) -> List[tuple]:
        """Get working hours for a specific date."""
        if not self.is_working_day(date):
            return []
        
        day_name = date.strftime("%A").lower()
        return self.working_hours.get(day_name, [])


def create_default_calendar() -> BusinessCalendar:
    """Create a default business calendar."""
    calendar = BusinessCalendar(name="default")
    
    if CALENDAR_AVAILABLE:
        # Add US holidays for current year
        us_holidays = USHolidays(years=datetime.now().year)
        calendar.holidays = [datetime.combine(date, time()) for date in us_holidays.keys()]
    
    return calendar


def create_resource_pool(name: str, capacity: int, skills: Optional[List[str]] = None) -> ResourcePool:
    """Create a resource pool with given capacity and skills."""
    return ResourcePool(
        name=name,
        capacity=capacity,
        skills=skills or [],
        cost_per_hour=50.0,  # Default hourly rate
        availability_schedule=None
    )
