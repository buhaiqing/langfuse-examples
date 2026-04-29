"""
Alert configuration loader tests.

Tests cover YAML config loading, rule validation, and error handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.observability.alert_config_loader import (
    AlertConfigLoader,
    load_alert_rules,
    validate_alert_config,
)
from src.observability.alerting import (
    AlertChannel,
    AlertSeverity,
)


class TestAlertConfigLoader:
    """AlertConfigLoader class tests."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock alert manager."""
        with patch('src.observability.alert_config_loader.get_alert_manager') as mock_get:
            manager = MagicMock()
            mock_get.return_value = manager
            yield manager

    def create_temp_config(self, config_dict: dict) -> str:
        """Helper to create temporary YAML config file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            yaml.dump(config_dict, f)
            return f.name

    def test_load_valid_single_rule(self, mock_manager):
        """Test loading a single valid alert rule."""
        config = {
            'alerts': [
                {
                    'name': 'test-rule',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            loader = AlertConfigLoader()
            count = loader.load_and_register(config_path)

            assert count == 1
            mock_manager.register_rule.assert_called_once()

            # Verify the registered rule
            registered_rule = mock_manager.register_rule.call_args[0][0]
            assert registered_rule.name == 'test-rule'
            assert registered_rule.metric == 'success_rate'
            assert registered_rule.threshold == 0.95
            assert registered_rule.severity == AlertSeverity.WARNING
        finally:
            Path(config_path).unlink()

    def test_load_multiple_rules(self, mock_manager):
        """Test loading multiple alert rules."""
        config = {
            'alerts': [
                {
                    'name': 'rule-1',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                },
                {
                    'name': 'rule-2',
                    'metric': 'latency_p95_ms',
                    'threshold': 500,
                    'operator': 'gt',
                    'severity': 'critical',
                },
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            loader = AlertConfigLoader()
            count = loader.load_and_register(config_path)
            assert count == 2
            assert mock_manager.register_rule.call_count == 2
        finally:
            Path(config_path).unlink()

    def test_load_with_channels(self, mock_manager):
        """Test loading rule with notification channels."""
        config = {
            'alerts': [
                {
                    'name': 'test',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                    'channels': ['wecom', 'slack'],
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            loader = AlertConfigLoader()
            loader.load_and_register(config_path)

            rule = mock_manager.register_rule.call_args[0][0]
            assert len(rule.channels) == 2
            assert AlertChannel.WEBHOOK in rule.channels
            assert AlertChannel.SLACK in rule.channels
        finally:
            Path(config_path).unlink()

    def test_load_skips_disabled_rules(self, mock_manager):
        """Test that disabled rules are not registered."""
        config = {
            'alerts': [
                {
                    'name': 'disabled-rule',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                    'enabled': False,
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            loader = AlertConfigLoader()
            count = loader.load_and_register(config_path)
            assert count == 0
            mock_manager.register_rule.assert_not_called()
        finally:
            Path(config_path).unlink()

    def test_missing_required_field_raises_error(self):
        """Test error when required field is missing."""
        config = {
            'alerts': [
                {
                    'name': 'test',
                    # Missing 'metric'
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            with patch('src.observability.alert_config_loader.get_alert_manager') as mock_get:
                mock_manager = MagicMock()
                mock_get.return_value = mock_manager

                loader = AlertConfigLoader()
                with pytest.raises(ValueError, match="Missing required field"):
                    loader.load_and_register(config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_operator_raises_error(self):
        """Test error when operator is invalid."""
        config = {
            'alerts': [
                {
                    'name': 'test',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'invalid_op',
                    'severity': 'warning',
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            with patch('src.observability.alert_config_loader.get_alert_manager') as mock_get:
                mock_manager = MagicMock()
                mock_get.return_value = mock_manager

                loader = AlertConfigLoader()
                with pytest.raises(ValueError, match="Invalid operator"):
                    loader.load_and_register(config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_severity_raises_error(self):
        """Test error when severity is invalid."""
        config = {
            'alerts': [
                {
                    'name': 'test',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'invalid_level',
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            with patch('src.observability.alert_config_loader.get_alert_manager') as mock_get:
                mock_manager = MagicMock()
                mock_get.return_value = mock_manager

                loader = AlertConfigLoader()
                with pytest.raises(ValueError, match="Invalid severity"):
                    loader.load_and_register(config_path)
        finally:
            Path(config_path).unlink()

    def test_invalid_threshold_type_raises_error(self):
        """Test error when threshold is not a number."""
        config = {
            'alerts': [
                {
                    'name': 'test',
                    'metric': 'success_rate',
                    'threshold': 'not_a_number',
                    'operator': 'lt',
                    'severity': 'warning',
                }
            ]
        }

        config_path = self.create_temp_config(config)

        try:
            with patch('src.observability.alert_config_loader.get_alert_manager') as mock_get:
                mock_manager = MagicMock()
                mock_get.return_value = mock_manager

                loader = AlertConfigLoader()
                with pytest.raises(ValueError, match="Threshold must be a number"):
                    loader.load_and_register(config_path)
        finally:
            Path(config_path).unlink()

    def test_empty_alerts_list(self, mock_manager):
        """Test loading with empty alerts list."""
        config = {'alerts': []}
        config_path = self.create_temp_config(config)

        try:
            loader = AlertConfigLoader()
            count = loader.load_and_register(config_path)
            assert count == 0
        finally:
            Path(config_path).unlink()


class TestValidateAlertConfig:
    """Configuration validation function tests."""

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = {
            'alerts': [
                {
                    'name': 'valid-rule',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            result = validate_alert_config(config_path)

            assert result['valid'] is True
            assert len(result['errors']) == 0
            assert result['rules_count'] == 1
            assert result['enabled_rules'] == 1
        finally:
            Path(config_path).unlink()

    def test_validate_file_not_found(self):
        """Test validation when file doesn't exist."""
        result = validate_alert_config("/nonexistent/config.yaml")

        assert result['valid'] is False
        assert len(result['errors']) > 0

    def test_validate_duplicate_names(self):
        """Test validation detects duplicate rule names."""
        config = {
            'alerts': [
                {
                    'name': 'duplicate',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                },
                {
                    'name': 'duplicate',
                    'metric': 'latency_p95_ms',
                    'threshold': 500,
                    'operator': 'gt',
                    'severity': 'critical',
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            result = validate_alert_config(config_path)

            assert result['valid'] is False
            assert any("Duplicate" in err for err in result['errors'])
        finally:
            Path(config_path).unlink()

    def test_validate_counts_disabled_rules(self):
        """Test validation counts disabled rules correctly."""
        config = {
            'alerts': [
                {
                    'name': 'enabled-rule',
                    'metric': 'success_rate',
                    'threshold': 0.95,
                    'operator': 'lt',
                    'severity': 'warning',
                    'enabled': True,
                },
                {
                    'name': 'disabled-rule',
                    'metric': 'latency_p95_ms',
                    'threshold': 500,
                    'operator': 'gt',
                    'severity': 'critical',
                    'enabled': False,
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            result = validate_alert_config(config_path)

            assert result['rules_count'] == 2
            assert result['enabled_rules'] == 1
            assert result['disabled_rules'] == 1
        finally:
            Path(config_path).unlink()


class TestLoadAlertRules:
    """Convenience function tests."""

    @patch('src.observability.alert_config_loader.AlertConfigLoader')
    def test_load_alert_rules_calls_loader(self, mock_loader_class):
        """Test that load_alert_rules uses AlertConfigLoader."""
        mock_loader = MagicMock()
        mock_loader.load_and_register.return_value = 5
        mock_loader_class.return_value = mock_loader

        result = load_alert_rules("/path/to/config.yaml")

        assert result == 5
        mock_loader_class.assert_called_once_with("/path/to/config.yaml")
        mock_loader.load_and_register.assert_called_once()
