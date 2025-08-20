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
    
    def export_to_xes(self, filename: str):
        """Export events to XES format for process mining."""
        # This is a simplified XES export
        xes_data = {
            "log": {
                "traces": self._group_events_by_case()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(xes_data, f, indent=2)
    
    def _group_events_by_case(self) -> Dict[str, List[Dict]]:
        """Group events by case ID."""
        cases = {}
        for event in self.events:
            if event.case_id not in cases:
                cases[event.case_id] = []
            cases[event.case_id].append(event.to_dict())
        
        # Sort events within each case by timestamp
        for case_events in cases.values():
            case_events.sort(key=lambda e: e["timestamp"])
        
        return cases


class MetricsCollector:
    """Collects and calculates process metrics."""
    
    def __init__(self, tracker: EventTracker):
        self.tracker = tracker
    
    def calculate_case_duration(self, case_id: str) -> Optional[float]:
        """Calculate duration of a case in seconds."""
        events = self.tracker.get_events(case_id=case_id)
        if len(events) < 2:
            return None
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        start_time = events[0].timestamp
        end_time = events[-1].timestamp
        
        return (end_time - start_time).total_seconds()
    
    def calculate_throughput(self, window_hours: float = 24.0) -> float:
        """Calculate throughput (cases per hour) over a time window."""
        if not self.tracker.events:
            return 0.0
        
        # Get unique case IDs in the last window_hours
        now = datetime.now()
        cutoff = now.timestamp() - (window_hours * 3600)
        
        recent_cases = set()
        for event in self.tracker.events:
            if event.timestamp.timestamp() > cutoff:
                recent_cases.add(event.case_id)
        
        return len(recent_cases) / window_hours
    
    def calculate_activity_frequency(self) -> Dict[str, int]:
        """Calculate frequency of each activity."""
        frequencies = {}
        for event in self.tracker.events:
            if event.activity:
                frequencies[event.activity] = frequencies.get(event.activity, 0) + 1
        return frequencies


# Global tracker instance
_global_tracker = EventTracker()

def get_tracker() -> EventTracker:
    """Get the global event tracker."""
    return _global_tracker

def log_event(event_type: str, case_id: str, activity: str = None, 
              resource: str = None, **data):
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