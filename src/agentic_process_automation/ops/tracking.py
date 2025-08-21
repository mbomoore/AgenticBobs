"""Tracking and monitoring for process execution.

Handles event logging, metrics collection, and execution tracking.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json


@dataclass
class Event:
    """Represents a process execution event."""
    timestamp: datetime
    event_type: str
    case_id: str
    activity: Optional[str] = None
    resource: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "case_id": self.case_id,
            "activity": self.activity,
            "resource": self.resource,
            "data": self.data
        }


class EventTracker:
    """Tracks process execution events."""
    
    def __init__(self):
        self.events: List[Event] = []
        self.callbacks: List[Callable[[Event], None]] = []
    
    def log_event(self, event: Event):
        """Log a process event."""
        self.events.append(event)
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")
    
    def add_callback(self, callback: Callable[[Event], None]):
        """Add an event callback."""
        self.callbacks.append(callback)
    
    def get_events(self, case_id: Optional[str] = None, 
                   event_type: Optional[str] = None) -> List[Event]:
        """Get events with optional filtering."""
        events = self.events
        
        if case_id:
            events = [e for e in events if e.case_id == case_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events


# Global tracker instance
_global_tracker = EventTracker()

def get_tracker() -> EventTracker:
    """Get the global event tracker."""
    return _global_tracker

def log_event(event_type: str, case_id: str, activity: Optional[str] = None, 
              resource: Optional[str] = None, **data):
    """Convenience function to log an event."""
    event = Event(
        timestamp=datetime.now(),
        event_type=event_type,
        case_id=case_id,
        activity=activity,
        resource=resource,
        data=data
    )
    _global_tracker.log_event(event)
