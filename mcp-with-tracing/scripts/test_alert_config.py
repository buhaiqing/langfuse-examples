#!/usr/bin/env python3
"""
Test alert configuration loading.

This script validates the alerts.yaml configuration file
without starting the full server.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.observability.alert_config_loader import AlertConfigLoader


def main():
    """Test loading alert rules from configuration."""
    print("="*60)
    print("Testing Alert Configuration Loading")
    print("="*60)
    
    # Default config path
    config_path = project_root / "config" / "alerts.yaml"
    
    if not config_path.exists():
        print(f"\n❌ Configuration file not found: {config_path}")
        print("\nPlease create config/alerts.yaml first.")
        print("See docs/alert-config-guide.md for examples.")
        sys.exit(1)
    
    print(f"\n📄 Configuration file: {config_path}")
    print("-"*60)
    
    try:
        loader = AlertConfigLoader(str(config_path))
        count = loader.load_and_register()
        
        print("\n" + "="*60)
        if count > 0:
            print(f"✅ SUCCESS: Loaded {count} alert rule(s)")
            print("\nLoaded rules:")
            for rule_name in loader.get_loaded_rules():
                print(f"  - {rule_name}")
            
            print("\n" + "="*60)
            print("Next steps:")
            print("  1. Start the server: python -m src.server")
            print("  2. Configure notification channels in .env")
            print("  3. Test alerts: python scripts/setup_wecom_alerts.py")
            print("="*60)
        else:
            print("⚠️  WARNING: No rules loaded")
            print("\nPossible reasons:")
            print("  - All rules are disabled (enabled: false)")
            print("  - Configuration file is empty")
            print("  - No 'alerts' section in YAML")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        print("\nPlease check the configuration file syntax.")
        print("See docs/alert-config-guide.md for correct format.")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
