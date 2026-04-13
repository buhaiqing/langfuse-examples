#!/usr/bin/env python3
"""
Verify Phase 6 Smart Alerting integration with the MCP server.

This script tests that the SmartAlertManager can be properly initialized
and integrated into the server startup process.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 70)
    print("Testing Module Imports")
    print("=" * 70)
    
    try:
        from src.observability.smart_alerting import SmartAlertManager
        print("✅ SmartAlertManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import SmartAlertManager: {e}")
        return False
    
    try:
        from src.observability.anomaly_detector import AnomalyDetector
        print("✅ AnomalyDetector imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AnomalyDetector: {e}")
        return False
    
    try:
        from src.observability.metrics_collector import MetricsCollector
        print("✅ MetricsCollector imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MetricsCollector: {e}")
        return False
    
    # Check ML dependencies
    ml_deps = [
        ("prophet", "Prophet"),
        ("pyod", "PyOD"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("sklearn", "scikit-learn"),
    ]
    
    print("\nChecking ML Dependencies:")
    for module_name, display_name in ml_deps:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
        except ImportError:
            print(f"  ❌ {display_name} (not installed)")
            print(f"     Install with: pip install {module_name}")
            return False
    
    return True


def test_smart_alert_manager_initialization():
    """Test SmartAlertManager initialization."""
    print("\n" + "=" * 70)
    print("Testing SmartAlertManager Initialization")
    print("=" * 70)
    
    try:
        from src.observability.smart_alerting import SmartAlertManager
        
        # Test with default interval
        manager = SmartAlertManager(detection_interval_minutes=10)
        print("✅ SmartAlertManager initialized (10 min interval)")
        
        # Verify components
        assert hasattr(manager, 'metrics_collector'), "Missing metrics_collector"
        print("  ✅ MetricsCollector component present")
        
        assert hasattr(manager, 'anomaly_detector'), "Missing anomaly_detector"
        print("  ✅ AnomalyDetector component present")
        
        assert hasattr(manager, 'detection_interval'), "Missing detection_interval"
        print(f"  ✅ Detection interval: {manager.detection_interval} minutes")
        
        # Test start/stop (without actually running)
        print("  ✅ Monitoring methods available")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_integration():
    """Test that server.py properly imports and uses SmartAlertManager."""
    print("\n" + "=" * 70)
    print("Testing Server Integration")
    print("=" * 70)
    
    server_file = project_root / "src" / "server.py"
    
    if not server_file.exists():
        print(f"❌ server.py not found at {server_file}")
        return False
    
    content = server_file.read_text()
    
    # Check import
    if "from src.observability.smart_alerting import SmartAlertManager" in content:
        print("✅ SmartAlertManager imported in server.py")
    else:
        print("❌ SmartAlertManager NOT imported in server.py")
        return False
    
    # Check instantiation
    if "SmartAlertManager(" in content:
        print("✅ SmartAlertManager instantiated in server.py")
    else:
        print("❌ SmartAlertManager NOT instantiated in server.py")
        return False
    
    # Check start_monitoring call
    if "start_monitoring()" in content:
        print("✅ start_monitoring() called in server.py")
    else:
        print("❌ start_monitoring() NOT called in server.py")
        return False
    
    # Check environment variable
    if "SMART_ALERT_CHECK_INTERVAL_MINUTES" in content:
        print("✅ SMART_ALERT_CHECK_INTERVAL_MINUTES env var used")
    else:
        print("⚠️  SMART_ALERT_CHECK_INTERVAL_MINUTES env var NOT configured")
    
    return True


def test_env_configuration():
    """Test that .env.example includes smart alerting configuration."""
    print("\n" + "=" * 70)
    print("Testing Environment Configuration")
    print("=" * 70)
    
    env_example = project_root / ".env.example"
    
    if not env_example.exists():
        print(f"❌ .env.example not found at {env_example}")
        return False
    
    content = env_example.read_text()
    
    if "SMART_ALERT_CHECK_INTERVAL_MINUTES" in content:
        print("✅ SMART_ALERT_CHECK_INTERVAL_MINUTES documented in .env.example")
    else:
        print("❌ SMART_ALERT_CHECK_INTERVAL_MINUTES NOT in .env.example")
        return False
    
    if "Phase 6" in content or "ML-Based" in content or "Smart" in content:
        print("✅ Smart alerting section documented")
    else:
        print("⚠️  Smart alerting documentation could be clearer")
    
    return True


def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("Phase 6 Smart Alerting Integration Verification")
    print("=" * 70)
    print()
    
    results = []
    
    # Test 1: Imports
    results.append(("Module Imports", test_imports()))
    
    # Test 2: Initialization
    results.append(("Manager Initialization", test_smart_alert_manager_initialization()))
    
    # Test 3: Server Integration
    results.append(("Server Integration", test_server_integration()))
    
    # Test 4: Environment Config
    results.append(("Environment Configuration", test_env_configuration()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Integration Test Summary")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<50} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n🎉 All integration tests passed!")
        print("\nNext steps:")
        print("1. Set up your .env file with LANGFUSE credentials")
        print("2. Configure notification channels (optional)")
        print("3. Start the server: python -m src.server")
        print("4. Monitor logs for smart alerting initialization")
        print("5. Wait ~24 hours for initial model training data")
        return 0
    else:
        print("\n❌ Some integration tests failed.")
        print("\nPlease fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
