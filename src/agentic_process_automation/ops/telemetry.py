"""Telemetry and observability for process automation.

Provides distributed tracing and metrics collection using OpenTelemetry.
"""
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class TelemetryProvider:
    """Provider for telemetry and observability."""
    
    def __init__(self, service_name: str = "agentic_process_automation"):
        self.service_name = service_name
        self.tracer = None
        self.enabled = False
        
        if OTEL_AVAILABLE:
            self._setup_tracing()
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing."""
        try:
            # Configure tracer provider
            trace.set_tracer_provider(TracerProvider())
            
            # Setup Jaeger exporter (optional)
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            self.tracer = trace.get_tracer(self.service_name)
            self.enabled = True
            
        except Exception as e:
            print(f"Failed to setup tracing: {e}")
            self.enabled = False
    
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
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        else:
            # No-op context when tracing is disabled
            yield None
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the current span."""
        if self.enabled:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.add_event(name, attributes or {})


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
        
        class MockSpan:
            def __init__(self, span_data):
                self.span_data = span_data
            
            def set_attribute(self, key: str, value: str):
                self.span_data["attributes"][key] = value
            
            def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
                self.span_data["events"].append({
                    "name": name,
                    "attributes": attributes or {}
                })
        
        try:
            yield MockSpan(span_data)
        except Exception as e:
            span_data["error"] = str(e)
            raise
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add a mock event."""
        self.events.append({
            "name": name,
            "attributes": attributes or {}
        })


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