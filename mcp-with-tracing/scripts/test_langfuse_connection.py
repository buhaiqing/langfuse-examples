#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from src.observability.config import ObservabilityConfig
from src.observability.langfuse_client import init_observer, get_observer

def test_langfuse_connection():
    print("=" * 60)
    print("Langfuse Connection Test")
    print("=" * 60)
    
    config = ObservabilityConfig()
    print(f"\nConfiguration loaded:")
    print(f"  - Public Key: {config.langfuse_public_key[:15]}...")
    print(f"  - Secret Key: {config.langfuse_secret_key[:15]}...")
    print(f"  - Host: {config.langfuse_host}")
    print(f"  - Configured: {config.is_configured()}")
    
    if not config.is_configured():
        print("\nERROR: Langfuse credentials not configured!")
        return False
    
    observer = init_observer(config)
    
    if not observer.client:
        print("\nERROR: Langfuse client not initialized!")
        return False
    
    print("\n✓ Langfuse client initialized successfully")
    
    test_session_id = f"test-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\nCreating test trace with session_id: {test_session_id}")
    
    try:
        with observer.trace_tool_call(
            tool_name="test_echo",
            input_args={"message": "Hello, Langfuse!"},
            session_id=test_session_id,
            user_id="test-user",
            prompt_version="v1.0",
        ) as observation:
            if observation:
                print(f"  Observation ID: {observation.id}")
                observation.update(output="Echo: Hello, Langfuse!")
        
        observer.flush()
        print("✓ Trace flushed to Langfuse")
        
        observer.shutdown()
        
        print("\n" + "=" * 60)
        print("TEST PASSED - Langfuse integration working!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\nERROR: Failed to submit trace: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("TEST FAILED")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_langfuse_connection()
    sys.exit(0 if success else 1)
