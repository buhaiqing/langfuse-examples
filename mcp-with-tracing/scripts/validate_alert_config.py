#!/usr/bin/env python3
"""
Validate alert configuration file.

This script checks the alerts.yaml file for syntax errors and validates
all rules without actually loading them into the server.

Usage:
    python scripts/validate_alert_config.py [config_path]
    
Examples:
    python scripts/validate_alert_config.py
    python scripts/validate_alert_config.py config/alerts.yaml
    python scripts/validate_alert_config.py config/alerts-prod.yaml
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.observability.alert_config_loader import validate_alert_config


def print_validation_result(result: dict, config_path: str) -> None:
    """Print validation results in a user-friendly format."""
    print("="*70)
    print(f"Alert Configuration Validation Report")
    print("="*70)
    print(f"\n📄 Configuration file: {config_path}")
    print("-"*70)
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total rules:     {result['rules_count']}")
    print(f"   Enabled rules:   {result['enabled_rules']}")
    print(f"   Disabled rules:  {result['disabled_rules']}")
    
    # Errors
    if result['errors']:
        print(f"\n❌ Errors ({len(result['errors'])}):")
        for i, error in enumerate(result['errors'], 1):
            print(f"   {i}. {error}")
    else:
        print(f"\n✅ No errors found")
    
    # Warnings
    if result['warnings']:
        print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
        for i, warning in enumerate(result['warnings'], 1):
            print(f"   {i}. {warning}")
    
    # Overall status
    print("\n" + "="*70)
    if result['valid']:
        print("✅ VALIDATION PASSED")
        print("="*70)
        print("\nThe configuration file is valid and ready to use.")
        print("\nNext steps:")
        print("  1. Start the server: python -m src.server")
        print("  2. Monitor logs for any runtime issues")
        print("  3. Test notifications: python scripts/setup_wecom_alerts.py")
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print("="*70)
        print("\nPlease fix the errors above before starting the server.")
        print("\nHelp:")
        print("  - See docs/alert-config-guide.md for configuration syntax")
        print("  - Check config/alerts.yaml.example for examples")
        return 1


def main():
    """Main entry point."""
    # Get config path from argument or use default
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = None
    
    print("\n🔍 Validating alert configuration...\n")
    
    try:
        result = validate_alert_config(config_path)
        
        # Determine actual path used
        if config_path:
            actual_path = config_path
        else:
            actual_path = str(project_root / "config" / "alerts.yaml")
        
        exit_code = print_validation_result(result, actual_path)
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"\n❌ Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
