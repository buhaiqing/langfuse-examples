"""
Grafana Dashboard Integration.

Provides tools to generate Grafana dashboards in JSON format
for visualizing skill observability metrics.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardConfig:
    """Configuration for Grafana dashboard."""

    title: str = "Skill Observability"
    uid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timezone: str = "browser"
    refresh: str = "30s"
    time_from: str = "now-6h"
    time_to: str = "now"


@dataclass
class PanelConfig:
    """Configuration for a dashboard panel."""

    title: str
    targets: list[str] = field(default_factory=list)
    panel_type: str = "graph"
    grid_pos: dict[str, int] = field(default_factory=lambda: {"h": 8, "w": 12, "x": 0, "y": 0})


class GrafanaDashboardGenerator:
    """
    Generator for Grafana dashboard JSON.

    Creates Grafana dashboards in JSON format that can be
    imported into Grafana for real-time visualization.

    Example:
        config = DashboardConfig(title="My Dashboard")
        generator = GrafanaDashboardGenerator(config)

        generator.add_graph_panel(
            title="Skill Executions",
            targets=["skill_executions_total"],
        )

        dashboard_json = generator.generate()
    """

    def __init__(self, config: DashboardConfig | None = None):
        """
        Initialize the dashboard generator.

        Args:
            config: Dashboard configuration
        """
        self.config = config or DashboardConfig()
        self._panels: list[dict[str, Any]] = []
        self._next_y: int = 0

    def add_graph_panel(
        self,
        title: str,
        targets: list[str],
        grid_pos: dict[str, int] | None = None,
    ) -> "GrafanaDashboardGenerator":
        """
        Add a graph panel to the dashboard.

        Args:
            title: Panel title
            targets: List of metric targets
            grid_pos: Grid position (h, w, x, y)

        Returns:
            Self for chaining
        """
        panel = {
            "title": title,
            "type": "graph",
            "id": len(self._panels) + 1,
            "gridPos": grid_pos or {"h": 8, "w": 12, "x": 0, "y": self._next_y},
            "targets": [{"expr": target, "refId": chr(65 + i)} for i, target in enumerate(targets)],
            "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        }

        self._panels.append(panel)
        self._next_y += (grid_pos or {}).get("h", 8)

        return self

    def add_singlestat_panel(
        self,
        title: str,
        target: str,
        unit: str = "percentunit",
    ) -> "GrafanaDashboardGenerator":
        """
        Add a single stat panel.

        Args:
            title: Panel title
            target: Metric target
            unit: Unit format

        Returns:
            Self for chaining
        """
        panel = {
            "title": title,
            "type": "singlestat",
            "id": len(self._panels) + 1,
            "gridPos": {"h": 4, "w": 4, "x": 0, "y": self._next_y},
            "targets": [{"expr": target, "refId": "A"}],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"color": "red", "value": None},
                            {"color": "yellow", "value": 0.5},
                            {"color": "green", "value": 0.8},
                        ],
                    },
                }
            },
        }

        self._panels.append(panel)
        self._next_y += 4

        return self

    def generate(self) -> dict[str, Any]:
        """
        Generate the complete dashboard JSON.

        Returns:
            Dashboard JSON suitable for Grafana import
        """
        return {
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "type": "dashboard",
                    }
                ]
            },
            "editable": True,
            "fiscalYearStartMonth": 0,
            "graphTooltip": 0,
            "id": None,
            "links": [],
            "liveNow": False,
            "panels": self._panels,
            "refresh": self.config.refresh,
            "schemaVersion": 38,
            "style": "dark",
            "tags": ["skill-observability"],
            "templating": {
                "list": [
                    {
                        "current": {"selected": False, "text": "prometheus", "value": "prometheus"},
                        "definition": "label_values(skill_executions_total, __name__)",
                        "hide": 0,
                        "includeAll": False,
                        "label": "Data Source",
                        "multi": False,
                        "name": "DS_PROMETHEUS",
                        "options": [],
                        "query": {"query": "label_values(skill_executions_total, __name__)", "refId": "StandardQuery1"},
                        "refresh": 1,
                        "regex": "",
                        "skipUrlSync": False,
                        "type": "query",
                    }
                ]
            },
            "time": {"from": self.config.time_from, "to": self.config.time_to},
            "timepicker": {},
            "timezone": self.config.timezone,
            "title": self.config.title,
            "uid": self.config.uid,
            "version": 1,
            "weekStart": "",
        }
