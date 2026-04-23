"""
HTTP Server for Prometheus metrics endpoint.

Provides a simple HTTP server that exposes /metrics endpoint
in Prometheus exposition format.
"""

import http.server
import socketserver
import threading
from typing import Any

from skill_observability_toolkit.integrations.prometheus_exporter import PrometheusExporter


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoint."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/metrics" or self.path == "/metrics/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()

            metrics_output = self.server.exporter.to_prometheus_format()
            self.wfile.write(metrics_output.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args):
        """Suppress default logging."""
        pass


class MetricsServer:
    """
    HTTP server for Prometheus metrics.

    Provides a simple HTTP server exposing metrics in Prometheus
    exposition format at /metrics endpoint.

    Example:
        server = MetricsServer(port=9090)
        server.start()

        # Or use with context manager
        with MetricsServer(port=9090) as server:
            # Server running in background
            pass
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 9090):
        """
        Initialize the metrics server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self._server: socketserver.TCPServer | None = None
        self._thread: threading.Thread | None = None
        self.exporter = PrometheusExporter(namespace="skill_obs")

    def start(self):
        """Start the metrics server in a background thread."""
        if self._server is not None:
            return

        self._server = socketserver.TCPServer((self.host, self.port), MetricsHandler)
        self._server.exporter = self.exporter

        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        """Stop the metrics server."""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None

    def __enter__(self) -> "MetricsServer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.stop()
