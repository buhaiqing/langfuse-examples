"""Tests for Grafana Dashboard Generator."""

import pytest
from skill_observability_toolkit.integrations.grafana_dashboard import (
    DashboardConfig,
    GrafanaDashboardGenerator,
    PanelConfig,
)


def test_dashboard_config_initialization():
    """Test DashboardConfig can be initialized."""
    config = DashboardConfig(title="Test Dashboard")
    assert config.title == "Test Dashboard"
    assert len(config.uid) == 8


def test_dashboard_generator_initialization():
    """Test GrafanaDashboardGenerator can be initialized."""
    config = DashboardConfig(title="Test Dashboard")
    generator = GrafanaDashboardGenerator(config)
    assert generator.config.title == "Test Dashboard"


def test_generate_dashboard_json():
    """Test dashboard JSON generation."""
    config = DashboardConfig(title="Skill Observability")
    generator = GrafanaDashboardGenerator(config)

    dashboard = generator.generate()

    assert dashboard["title"] == "Skill Observability"
    assert "panels" in dashboard
    assert "templating" in dashboard
    assert dashboard["refresh"] == "30s"


def test_add_graph_panel_to_dashboard():
    """Test adding graph panel."""
    config = DashboardConfig(title="Custom Dashboard")
    generator = GrafanaDashboardGenerator(config)

    generator.add_graph_panel(title="Skill Executions", targets=["skill_executions_total"])

    dashboard = generator.generate()
    assert len(dashboard["panels"]) > 0
    assert dashboard["panels"][0]["title"] == "Skill Executions"
    assert dashboard["panels"][0]["type"] == "graph"


def test_add_singlestat_panel():
    """Test adding single stat panel."""
    config = DashboardConfig(title="Stats Dashboard")
    generator = GrafanaDashboardGenerator(config)

    generator.add_singlestat_panel(title="Trust Score", target="trust_score")

    dashboard = generator.generate()

    stat_panel = dashboard["panels"][0]
    assert stat_panel["title"] == "Trust Score"
    assert stat_panel["type"] == "singlestat"
    assert stat_panel["fieldConfig"]["defaults"]["unit"] == "percentunit"


def test_multiple_panels():
    """Test adding multiple panels."""
    config = DashboardConfig(title="Multi Panel Dashboard")
    generator = GrafanaDashboardGenerator(config)

    generator.add_graph_panel(title="Executions", targets=["executions_total"])
    generator.add_graph_panel(title="Latency", targets=["latency_seconds"])
    generator.add_singlestat_panel(title="Trust Score", target="trust_score")

    dashboard = generator.generate()

    assert len(dashboard["panels"]) == 3
    assert dashboard["panels"][0]["title"] == "Executions"
    assert dashboard["panels"][1]["title"] == "Latency"
    assert dashboard["panels"][2]["title"] == "Trust Score"


def test_panel_config_dataclass():
    """Test PanelConfig dataclass."""
    panel = PanelConfig(title="Test Panel", targets=["metric1"], panel_type="graph")
    assert panel.title == "Test Panel"
    assert panel.targets == ["metric1"]
    assert panel.panel_type == "graph"
