"""Core services with dependency injection."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from .events import Event, EventType, event_bus
from .pir import PIR, validate

class ProcessService:
    """Core business logic for process operations."""

    def __init__(self, ai_service, validator_service):
        self.ai_service = ai_service
        self.validator_service = validator_service
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        event_bus.subscribe(EventType.PROCESS_GENERATE_REQUEST, self._handle_generate)
        event_bus.subscribe(EventType.PROCESS_VALIDATE_REQUEST, self._handle_validate)
        event_bus.subscribe(EventType.PROCESS_REFINE_REQUEST, self._handle_refine)

    async def _handle_generate(self, event: Event):
        """Handle process generation requests."""
        try:
            xml = await self.ai_service.generate_process_xml(
                event.data["description"],
                event.data.get("process_type", "BPMN")
            )

            response = Event(
                type=EventType.PROCESS_GENERATE_RESPONSE,
                data={"xml": xml, "success": True},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(response)

        except Exception as e:
            error_response = Event(
                type=EventType.PROCESS_GENERATE_RESPONSE,
                data={"error": str(e), "success": False},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(error_response)

    async def _handle_validate(self, event: Event):
        """Handle validation requests."""
        result = self.validator_service.validate_bpmn_xml(event.data["xml"])

        response = Event(
            type=EventType.PROCESS_VALIDATE_RESPONSE,
            data={"validation_result": result},
            source="process_service",
            correlation_id=event.correlation_id
        )
        await event_bus.publish(response)

    async def _handle_refine(self, event: Event):
        """Handle process refinement requests."""
        try:
            xml = await self.ai_service.refine_process(
                event.data["current_xml"],
                event.data["feedback"]
            )

            response = Event(
                type=EventType.PROCESS_REFINE_RESPONSE,
                data={"xml": xml, "success": True},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(response)

        except Exception as e:
            error_response = Event(
                type=EventType.PROCESS_REFINE_RESPONSE,
                data={"error": str(e), "success": False},
                source="process_service",
                correlation_id=event.correlation_id
            )
            await event_bus.publish(error_response)

class AIService(ABC):
    """Abstract interface for AI services."""

    @abstractmethod
    async def generate_process_xml(self, description: str, process_type: str) -> str:
        pass

    @abstractmethod
    async def refine_process(self, current_xml: str, feedback: str) -> str:
        pass

class ValidatorService:
    """Unified validation service."""

    def validate_bpmn_xml(self, xml: str) -> Dict[str, Any]:
        try:
            from .adapters.bpmn import parse_bpmn
            pir = parse_bpmn(xml.encode('utf-8'))
            result = validate(pir)
            return {
                "is_valid": len(result["errors"]) == 0,
                "errors": result["errors"],
                "warnings": result["warnings"]
            }
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Parse error: {str(e)}"],
                "warnings": []
            }
