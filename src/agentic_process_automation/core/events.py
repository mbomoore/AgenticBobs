"""Event-driven architecture for AgenticBobs."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

class EventType(Enum):
    PROCESS_GENERATE_REQUEST = "process.generate.request"
    PROCESS_GENERATE_RESPONSE = "process.generate.response"
    PROCESS_VALIDATE_REQUEST = "process.validate.request"
    PROCESS_VALIDATE_RESPONSE = "process.validate.response"
    PROCESS_REFINE_REQUEST = "process.refine.request"
    PROCESS_REFINE_RESPONSE = "process.refine.response"
    UI_STATE_CHANGE = "ui.state.change"
    ERROR_OCCURRED = "error.occurred"

@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None
    timestamp: Optional[float] = None

class EventBus:
    """Central event bus for all AgenticBobs communication."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to events of a specific type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event):
        """Publish an event to all subscribers."""
        await self._queue.put(event)

    async def start_processing(self):
        """Start the event processing loop."""
        while True:
            event = await self._queue.get()
            await self._handle_event(event)

    async def _handle_event(self, event: Event):
        """Handle a single event by calling all subscribers."""
        if event.type in self._subscribers:
            for handler in self._subscribers[event.type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    error_event = Event(
                        type=EventType.ERROR_OCCURRED,
                        data={"error": str(e), "original_event": event},
                        source="event_bus"
                    )
                    # Don't await to prevent infinite loops
                    asyncio.create_task(self.publish(error_event))

# Global event bus instance
event_bus = EventBus()
