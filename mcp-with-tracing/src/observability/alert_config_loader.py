"""
Alert rule configuration loader.

Loads alert rules from YAML configuration file and registers them with AlertManager.
Supports environment-specific overrides via environment variables.
"""

import logging
from pathlib import Path

import yaml

from src.observability.alerting import (
    AlertChannel,
    AlertRule,
    AlertSeverity,
    get_alert_manager,
)

logger = logging.getLogger(__name__)


# Channel name mapping (config file -> enum)
CHANNEL_MAP = {
    "wecom": AlertChannel.WEBHOOK,  # WeCom uses WEBHOOK channel type
    "slack": AlertChannel.SLACK,
    "email": AlertChannel.EMAIL,
    "pagerduty": AlertChannel.PAGERDUTY,
    "webhook": AlertChannel.WEBHOOK,
}

# Severity mapping (config file -> enum)
SEVERITY_MAP = {
    "info": AlertSeverity.INFO,
    "warning": AlertSeverity.WARNING,
    "critical": AlertSeverity.CRITICAL,
}


class AlertConfigLoader:
    """
    Loads and registers alert rules from YAML configuration.
    
    Usage:
        loader = AlertConfigLoader()
        loader.load_and_register("config/alerts.yaml")
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize the alert config loader.
        
        Args:
            config_path: Path to alerts.yaml file. If None, uses default location.
        """
        if config_path is None:
            # Default: project_root/config/alerts.yaml
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "config" / "alerts.yaml"
        else:
            self.config_path = Path(config_path)

        self._manager = get_alert_manager()
        self._loaded_rules = []

    def load_and_register(self, config_path: str | None = None) -> int:
        """
        Load alert rules from YAML and register them with AlertManager.
        
        Args:
            config_path: Optional override for config file path.
            
        Returns:
            Number of rules successfully registered.
        """
        path = Path(config_path) if config_path else self.config_path

        if not path.exists():
            logger.warning("Alert config file not found: %s", path)
            logger.info("No alert rules will be loaded.")
            return 0

        try:
            with open(path, encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config or 'alerts' not in config:
                logger.warning("No 'alerts' section found in %s", path)
                return 0

            alerts_config = config['alerts']
            registered_count = 0

            for alert_cfg in alerts_config:
                try:
                    rule = self._create_rule_from_config(alert_cfg)
                    if rule and rule.enabled:
                        self._manager.register_rule(rule)
                        self._loaded_rules.append(rule.name)
                        registered_count += 1
                        logger.info("Registered alert rule: %s", rule.name)
                    elif rule and not rule.enabled:
                        logger.info("Skipped disabled rule: %s", alert_cfg.get('name', 'unknown'))
                except ValueError as e:
                    logger.error("Validation error for rule '%s': %s", alert_cfg.get('name', 'unknown'), e)
                    raise
                except Exception as e:
                    logger.error("Failed to register rule '%s': %s", alert_cfg.get('name', 'unknown'), e)

            logger.info("Loaded %d alert rule(s) from %s", registered_count, path)
            return registered_count

        except yaml.YAMLError as e:
            logger.error("Failed to parse alert config file: %s", e)
            raise
        except Exception as e:
            logger.error("Failed to load alert config: %s", e)
            raise

    def _create_rule_from_config(self, config: dict) -> AlertRule | None:
        """
        Create an AlertRule from configuration dictionary.
        
        Args:
            config: Rule configuration dictionary.
            
        Returns:
            AlertRule instance or None if invalid.
            
        Raises:
            ValueError: If configuration is invalid.
        """
        # Validate required fields
        required_fields = ['name', 'metric', 'threshold', 'operator', 'severity']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in alert rule config")

        # Validate rule name
        name = config['name']
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Rule 'name' must be a non-empty string")
        if not name.replace('-', '').replace('_', '').isalnum():
            raise ValueError(f"Rule name '{name}' contains invalid characters. Use only alphanumeric, hyphens, and underscores")

        # Validate metric
        metric = config['metric']
        if not isinstance(metric, str) or not metric.strip():
            raise ValueError("Metric must be a non-empty string")

        # Validate threshold
        try:
            threshold = float(config['threshold'])
        except (TypeError, ValueError):
            raise ValueError(f"Threshold must be a number, got: {config['threshold']}")

        # Validate operator
        operator = config['operator'].lower()
        valid_operators = ['gt', 'lt', 'gte', 'lte', 'eq']
        if operator not in valid_operators:
            raise ValueError(f"Invalid operator '{operator}'. Must be one of: {valid_operators}")

        # Validate severity
        severity_str = config['severity'].lower()
        if severity_str not in SEVERITY_MAP:
            raise ValueError(f"Invalid severity '{severity_str}'. Must be one of: {list(SEVERITY_MAP.keys())}")
        severity = SEVERITY_MAP[severity_str]

        # Validate window_minutes
        window_minutes = config.get('window_minutes', 60)
        try:
            window_minutes = int(window_minutes)
            if window_minutes <= 0:
                raise ValueError("window_minutes must be positive")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid window_minutes: {window_minutes}. Must be a positive integer") from e

        # Validate channels
        channels = []
        channels_config = config.get('channels', [])
        if not isinstance(channels_config, list):
            raise ValueError(f"'channels' must be a list, got: {type(channels_config).__name__}")

        for channel_name in channels_config:
            if not isinstance(channel_name, str):
                raise ValueError(f"Channel name must be a string, got: {type(channel_name).__name__}")
            channel_lower = channel_name.lower()
            if channel_lower in CHANNEL_MAP:
                channels.append(CHANNEL_MAP[channel_lower])
            else:
                logger.warning("Unknown channel '%s', skipping. Valid channels: %s", channel_name, list(CHANNEL_MAP.keys()))

        # Validate enabled
        enabled = config.get('enabled', True)
        if not isinstance(enabled, bool):
            raise ValueError(f"'enabled' must be a boolean, got: {type(enabled).__name__}")

        # Validate metadata
        metadata = config.get('metadata', {})
        if not isinstance(metadata, dict):
            raise ValueError(f"'metadata' must be a dictionary, got: {type(metadata).__name__}")

        # Create rule
        rule = AlertRule(
            name=name,
            metric=metric,
            threshold=threshold,
            operator=operator,
            severity=severity,
            window_minutes=window_minutes,
            channels=channels,
            enabled=enabled,
            metadata=metadata,
        )

        # Add description to metadata if present
        if 'description' in config:
            rule.metadata['description'] = config['description']

        return rule

    def get_loaded_rules(self) -> list[str]:
        """Get list of successfully loaded rule names."""
        return self._loaded_rules.copy()


def load_alert_rules(config_path: str | None = None) -> int:
    """
    Convenience function to load alert rules from config.
    
    Args:
        config_path: Optional path to alerts.yaml file.
        
    Returns:
        Number of rules registered.
    """
    loader = AlertConfigLoader(config_path)
    return loader.load_and_register()


def validate_alert_config(config_path: str | None = None) -> dict:
    """
    Validate alert configuration file without loading it.
    
    This function checks the configuration file for syntax errors
    and validates all rules without actually registering them.
    
    Args:
        config_path: Optional path to alerts.yaml file.
        
    Returns:
        Dictionary with validation results:
        {
            'valid': bool,
            'errors': list[str],
            'warnings': list[str],
            'rules_count': int,
            'enabled_rules': int,
            'disabled_rules': int
        }
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'rules_count': 0,
        'enabled_rules': 0,
        'disabled_rules': 0,
    }

    path = Path(config_path) if config_path else Path(__file__).parent.parent.parent / "config" / "alerts.yaml"

    if not path.exists():
        result['valid'] = False
        result['errors'].append(f"Configuration file not found: {path}")
        return result

    try:
        with open(path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result['valid'] = False
        result['errors'].append(f"YAML syntax error: {e}")
        return result

    if not config or 'alerts' not in config:
        result['valid'] = False
        result['errors'].append("No 'alerts' section found in configuration")
        return result

    alerts_config = config['alerts']
    if not isinstance(alerts_config, list):
        result['valid'] = False
        result['errors'].append(f"'alerts' must be a list, got: {type(alerts_config).__name__}")
        return result

    result['rules_count'] = len(alerts_config)

    # Validate each rule
    seen_names = set()
    for i, alert_cfg in enumerate(alerts_config):
        rule_num = i + 1

        if not isinstance(alert_cfg, dict):
            result['errors'].append(f"Rule #{rule_num}: Must be a dictionary")
            result['valid'] = False
            continue

        rule_name = alert_cfg.get('name', f'Rule #{rule_num}')

        # Check for duplicate names
        if rule_name in seen_names:
            result['errors'].append(f"Rule '{rule_name}': Duplicate rule name")
            result['valid'] = False
        seen_names.add(rule_name)

        # Try to create rule (will catch validation errors)
        try:
            loader = AlertConfigLoader()
            rule = loader._create_rule_from_config(alert_cfg)

            if rule:
                if rule.enabled:
                    result['enabled_rules'] += 1
                else:
                    result['disabled_rules'] += 1

        except ValueError as e:
            result['errors'].append(f"Rule '{rule_name}': {e!s}")
            result['valid'] = False
        except Exception as e:
            result['errors'].append(f"Rule '{rule_name}': Unexpected error - {e}")
            result['valid'] = False

    # Add warnings
    if result['rules_count'] == 0:
        result['warnings'].append("No rules defined in configuration")

    if result['enabled_rules'] == 0 and result['rules_count'] > 0:
        result['warnings'].append("All rules are disabled")

    return result
