"""Abstract frontend interface with dependency injection."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.events import Event, EventType, event_bus
import uuid

class Frontend(ABC):
    """Abstract base class for all AgenticBobs frontends."""

    def __init__(self, name: str):
        self.name = name
        self._session_data: Dict[str, Any] = {}
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Override in subclasses to handle specific events."""
        pass

    async def generate_process(self, description: str, process_type: str = "BPMN") -> str:
        """Request process generation and wait for response."""
        correlation_id = str(uuid.uuid4())

        # Set up response handler
        response_received = False
        result = {}

        def handle_response(event: Event):
            nonlocal response_received, result
            if event.correlation_id == correlation_id:
                result.update(event.data)
                response_received = True

        event_bus.subscribe(EventType.PROCESS_GENERATE_RESPONSE, handle_response)

        # Send request
        request = Event(
            type=EventType.PROCESS_GENERATE_REQUEST,
            data={"description": description, "process_type": process_type},
            source=self.name,
            correlation_id=correlation_id
        )
        await event_bus.publish(request)

        # Wait for response (simplified - in real implementation use proper async patterns)
        import asyncio
        timeout = 30
        elapsed = 0
        while not response_received and elapsed < timeout:
            await asyncio.sleep(0.1)
            elapsed += 0.1

        if not response_received:
            raise TimeoutError("Process generation timed out")

        if not result.get("success"):
            raise Exception(result.get("error", "Unknown error"))

        return result["xml"]

    @abstractmethod
    async def start(self):
        """Start the frontend interface."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the frontend interface."""
        pass

# Frontend implementations
class StreamlitFrontend(Frontend):
    """Streamlit-based frontend."""

    def __init__(self):
        super().__init__("streamlit")

    async def start(self):
        # Import and start existing Streamlit app
        import subprocess
        subprocess.run([
            "streamlit", "run",
            "src/agentic_process_automation/app/main.py"
        ])

class FastAPIFrontend(Frontend):
    """FastAPI-based frontend."""

    def __init__(self):
        super().__init__("fastapi")
        self.app = None

    async def start(self):
        # Import and start existing FastAPI app
        from backend.main import app
        self.app = app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)

class VueFrontend(Frontend):
    """Vue.js-based frontend."""

    def __init__(self):
        super().__init__("vue")

    async def start(self):
        # Start Vue development server
        import subprocess
        subprocess.run(["npm", "run", "dev"], cwd="thebobs")

# Frontend factory
class FrontendFactory:
    @staticmethod
    def create(frontend_type: str) -> Frontend:
        if frontend_type == "streamlit":
            return StreamlitFrontend()
        elif frontend_type == "fastapi":
            return FastAPIFrontend()
        elif frontend_type == "vue":
            return VueFrontend()
        else:
            raise ValueError(f"Unknown frontend type: {frontend_type}")
