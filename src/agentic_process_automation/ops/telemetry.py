"""Telemetry and observability for process automation.

Provides distributed tracing and metrics collection using OpenTelemetry.
"""
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class TelemetryProvider:
    """Provider for telemetry and observability."""
    
    def __init__(self, service_name: str = "agentic_process_automation"):
        self.service_name = service_name
        self.tracer = None
        self.enabled = OTEL_AVAILABLE
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a traced operation context."""
        if self.enabled and self.tracer:
            with self.tracer.start_as_current_span(operation_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))
                try:
                    yield span
                except Exception as e:
                    span.record_exception(e)
                    raise
        else:
            # No-op context when tracing is disabled
            yield None


class MockTelemetryProvider:
    """Mock telemetry provider for testing."""
    
    def __init__(self, service_name: str = "agentic_process_automation"):
        self.service_name = service_name
        self.enabled = True
        self.events = []
        self.spans = []
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Mock traced operation context."""
        span_data = {
            "operation_name": operation_name,
            "attributes": attributes or {},
            "events": []
        }
        self.spans.append(span_data)
        
        try:
            yield span_data
        except Exception as e:
            span_data["error"] = str(e)
            raise


# Global telemetry provider
_telemetry_provider = None

def get_telemetry() -> TelemetryProvider:
    """Get the global telemetry provider."""
    global _telemetry_provider
    if _telemetry_provider is None:
        if OTEL_AVAILABLE:
            _telemetry_provider = TelemetryProvider()
        else:
            _telemetry_provider = MockTelemetryProvider()
    return _telemetry_provider

def configure_telemetry(service_name: str = "agentic_process_automation"):
    """Configure global telemetry provider."""
    global _telemetry_provider
    if OTEL_AVAILABLE:
        _telemetry_provider = TelemetryProvider(service_name)
    else:
        _telemetry_provider = MockTelemetryProvider(service_name)
    return _telemetry_provider
