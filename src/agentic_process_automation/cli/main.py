"""Main application runner with dependency injection."""
import asyncio
from typing import List, Optional
from .core.events import event_bus
from .core.services import ProcessService, ValidatorService
from .frontends.base import FrontendFactory

class AgenticBobsApp:
    """Main application orchestrator."""

    def __init__(self):
        self.services = {}
        self.frontends: List = []
        self._setup_services()

    def _setup_services(self):
        """Initialize core services with dependency injection."""
        from .core.ai_service import MarvinAIService

        # Create services
        ai_service = MarvinAIService()
        validator_service = ValidatorService()

        # Register services
        self.services['ai'] = ai_service
        self.services['validator'] = validator_service
        self.services['process'] = ProcessService(ai_service, validator_service)

    def add_frontend(self, frontend_type: str):
        """Add a frontend to the application."""
        frontend = FrontendFactory.create(frontend_type)
        self.frontends.append(frontend)

    async def start(self, frontends: Optional[List[str]] = None):
        """Start the application with specified frontends."""
        if frontends is None:
            frontends = ["fastapi"]  # Default to API only

        # Add requested frontends
        for frontend_type in frontends:
            self.add_frontend(frontend_type)

        # Start event processing
        event_task = asyncio.create_task(event_bus.start_processing())

        # Start frontends
        frontend_tasks = []
        for frontend in self.frontends:
            task = asyncio.create_task(frontend.start())
            frontend_tasks.append(task)

        # Wait for all tasks
        await asyncio.gather(event_task, *frontend_tasks)

# Simple CLI
def main():
    import sys

    app = AgenticBobsApp()

    if len(sys.argv) == 1:
        # Default: run FastAPI + Vue
        frontends = ["fastapi", "vue"]
    else:
        # Allow specifying frontends
        frontends = sys.argv[1:]

    print(f"🤖 Starting AgenticBobs with frontends: {frontends}")
    asyncio.run(app.start(frontends))

if __name__ == "__main__":
    main()
