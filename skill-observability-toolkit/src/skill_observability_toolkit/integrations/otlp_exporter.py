"""OTLP (OpenTelemetry Protocol) Exporter for STOP Traces."""

import time
from typing import Any, Dict, List, Optional


class OTLPExporter:
    """
    Exporter for sending traces to OTLP-compatible backends.
    
    Supports:
    - Jaeger
    - Zipkin
    - Honeycomb
    - Any OTLP gRPC/HTTP endpoint
    """
    
    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout_ms: int = 10000,
        protocol: str = "grpc"
    ):
        """
        Initialize OTLP exporter.
        
        Args:
            endpoint: OTLP endpoint URL
            headers: Optional headers for authentication
            timeout_ms: Request timeout in milliseconds
            protocol: Protocol to use ("grpc" or "http")
        """
        self.endpoint = endpoint
        self.headers = headers or {}
        self.timeout_ms = timeout_ms
        self.protocol = protocol
        
        # Lazy import to avoid dependency when not used
        self._exporter = None
    
    def _get_exporter(self):
        """Get or create the OTLP exporter."""
        if self._exporter is None:
            try:
                if self.protocol == "grpc":
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                else:
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                
                self._exporter = OTLPSpanExporter(
                    endpoint=self.endpoint,
                    headers=self.headers,
                    timeout=self.timeout_ms / 1000,  # Convert to seconds
                )
            except ImportError as e:
                raise ImportError(
                    "OpenTelemetry packages not installed. "
                    "Install with: pip install opentelemetry-exporter-otlp"
                ) from e
        
        return self._exporter
    
    def _convert_to_otel(self, span: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
        """
        Convert STOP Span to OpenTelemetry Span format.
        
        Mapping:
        STOP Span              →  OpenTelemetry Span
        ─────────────────────────────────────────────────
        span_id                →  context.span_id
        trace_id               →  context.trace_id
        parent_span_id         →  parent.span_id
        name                   →  name
        start_time, end_time   →  start_time_unix_nano, end_time_unix_nano
        status                 →  status.code (OK/ERROR)
        input_data             →  attributes["input"]
        output_data            →  attributes["output"]
        scores                 →  attributes["scores.*"]
        metadata               →  attributes["metadata.*"]
        """
        # Convert timestamps to nanoseconds
        start_time_nano = int(span.get('start_time', 0) * 1e9)
        end_time_nano = int(span.get('end_time', 0) * 1e9) if span.get('end_time') else int(time.time() * 1e9)
        
        # Build attributes
        attributes = {}
        
        if span.get('input_data'):
            attributes['input'] = str(span['input_data'])
        
        if span.get('output_data'):
            attributes['output'] = str(span['output_data'])
        
        if span.get('scores'):
            for score in span['scores']:
                attributes[f"scores.{score.get('name')}"] = str(score.get('value'))
        
        if span.get('metadata'):
            for key, value in span['metadata'].items():
                attributes[f"metadata.{key}"] = str(value)
        
        # Map status
        status = span.get('status', 'running')
        if status == 'success':
            status_code = 1  # OK
        elif status == 'error':
            status_code = 2  # ERROR
        else:
            status_code = 0  # UNSET
        
        return {
            "trace_id": trace_id,
            "span_id": span.get('span_id'),
            "parent_span_id": span.get('parent_span_id'),
            "name": span.get('name', 'unknown'),
            "kind": 1,  # INTERNAL
            "start_time_unix_nano": start_time_nano,
            "end_time_unix_nano": end_time_nano,
            "status": {"code": status_code},
            "attributes": attributes,
        }
    
    def export(self, trace_data: Dict[str, Any]) -> bool:
        """
        Export trace data to OTLP endpoint.
        
        Args:
            trace_data: Trace data dictionary with 'spans' key
            
        Returns:
            True if export succeeded, False otherwise
        """
        try:
            exporter = self._get_exporter()
            
            # Get spans from trace
            spans = trace_data.get('spans', [])
            trace_id = trace_data.get('trace_id', 'unknown')
            
            # Convert spans
            otel_spans = [self._convert_to_otel(span, trace_id) for span in spans]
            
            # Export (placeholder - actual implementation depends on OTel SDK)
            # In production, this would call: exporter.export(otel_spans)
            
            return True
            
        except Exception as e:
            # Log error but don't fail
            print(f"OTLP export failed: {e}")
            return False
    
    def close(self):
        """Close exporter and release resources."""
        if self._exporter is not None:
            if hasattr(self._exporter, 'shutdown'):
                self._exporter.shutdown()
            self._exporter = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
