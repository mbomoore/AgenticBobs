"""Operations and monitoring components for process automation.

Contains tracking, telemetry, storage, and optimization tools.
"""

from .tracking import EventTracker, get_tracker, log_event

try:
    from .telemetry import get_telemetry, configure_telemetry
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    def get_telemetry():
        return None
    def configure_telemetry(service_name="agentic_process_automation"):
        return None

try:
    from .storage import create_storage_provider
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    def create_storage_provider(db_path=":memory:"):
        return None

try:
    from .optimize_roster import create_roster_optimizer
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    def create_roster_optimizer():
        return None

__all__ = [
    "EventTracker", "get_tracker", "log_event",
    "get_telemetry", "configure_telemetry",
    "create_storage_provider", "create_roster_optimizer"
]
