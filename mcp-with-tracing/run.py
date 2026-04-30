#!/usr/bin/env python
"""
Quick start script for MCP Langfuse Observability Server.

Usage:
    python run.py              # Start the MCP server
    python run.py --help       # Show this help message
"""

import os
import sys
from pathlib import Path
from datetime import datetime


def print_banner():
    """Print startup banner."""
    print("=" * 80)
    print("🚀 MCP Langfuse Observability Server")
    print("=" * 80)
    print()


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("📋 [1/5] Checking environment configuration...")
    
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("   ❌ .env file not found!")
        print("   💡 Solution: cp .env.example .env")
        print()
        return False
    
    print("   ✅ .env file found")
    
    # Read and check required variables
    with open(env_file, "r") as f:
        env_content = f.read()
    
    required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in env_content or f"{var}=your-" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"   ⚠️  Missing or placeholder values for: {', '.join(missing_vars)}")
        print("   💡 Please update .env with your actual Langfuse API keys")
        print("   💡 Get keys from: https://cloud.langfuse.com")
        print()
        return False
    
    print("   ✅ Required environment variables configured")
    print()
    return True


def check_dependencies():
    """Check if required Python packages are installed."""
    print("📦 [2/5] Checking dependencies...")
    
    required_packages = {
        "fastmcp": "FastMCP framework",
        "langfuse": "Langfuse SDK",
        "pydantic": "Pydantic validation",
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"   ✅ {package} ({description})")
        except ImportError:
            print(f"   ❌ {package} ({description}) - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print()
        print(f"   💡 Install missing packages: uv pip install {' '.join(missing)}")
        print("   💡 Or run: uv sync")
        print()
        return False
    
    print("   ✅ All required dependencies installed")
    print()
    return True


def check_project_structure():
    """Check if project structure is correct."""
    print("📁 [3/5] Checking project structure...")
    
    project_root = Path(__file__).parent
    
    required_dirs = ["src", "tests", "src/observability"]
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            print(f"   ❌ Missing directory: {dir_path}")
            print()
            return False
        print(f"   ✅ {dir_path}/")
    
    print("   ✅ Project structure is correct")
    print()
    return True


def show_config_info():
    """Display current configuration."""
    print("⚙️  [4/5] Current configuration:")
    
    config_items = {
        "LANGFUSE_HOST": "https://cloud.langfuse.com",
        "APP_ENV": "development",
        "LOG_LEVEL": "INFO",
        "ALERT_CHECK_INTERVAL_MINUTES": "5",
        "SMART_ALERT_CHECK_INTERVAL_MINUTES": "10",
    }
    
    for var, default in config_items.items():
        value = os.getenv(var, default)
        # Mask sensitive values
        if "KEY" in var or "SECRET" in var:
            value = value[:10] + "***" if len(value) > 10 else "***"
        print(f"   • {var}={value}")
    
    print()


def print_startup_info():
    """Print startup information."""
    print("🔧 [5/5] Starting server...")
    print()
    print("=" * 80)
    print(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Project root: {Path(__file__).parent.absolute()}")
    print(f"🐍 Python version: {sys.version}")
    print("=" * 80)
    print()


def print_access_guide():
    """Print access guide for frontend users and developers."""
    print("📖 Access Guide")
    print("=" * 80)
    print()
    
    print("🔌 MCP Server Access:")
    print("-" * 80)
    print("  • Transport: Stdio (default for MCP)")
    print("  • Protocol: JSON-RPC 2.0")
    print("  • Status: Server will listen for stdin/stdout connections")
    print()
    
    print("🛠️  Available MCP Tools:")
    print("-" * 80)
    tools = [
        ("health_check", "Check server health and component status"),
        ("submit_feedback_accept", "Submit positive feedback (accept)"),
        ("submit_feedback_reject", "Submit negative feedback (reject)"),
        ("submit_feedback_rating", "Submit rating (1-5)"),
        ("submit_feedback_comment", "Submit text comment"),
    ]
    for i, (name, desc) in enumerate(tools, 1):
        print(f"  {i}. {name}")
        print(f"     → {desc}")
    print()
    
    print("🌐 Frontend Integration:")
    print("-" * 80)
    print("  • MCP Inspector (recommended for testing):")
    print("    npm install -g @anthropic/mcp-inspector")
    print("    mcp-inspector")
    print("    → Open: http://localhost:5173")
    print()
    print("  • Claude Desktop:")
    print("    Add to claude_desktop_config.json:")
    print('    {')
    print('      "mcpServers": {')
    print('        "langfuse-observability": {')
    print(f'          "command": "python",')
    print(f'          "args": ["{Path(__file__).parent.absolute() / "run.py"}"]')
    print('        }')
    print('      }')
    print('    }')
    print()
    print("  • Cursor / VS Code:")
    print("    Configure in MCP settings to use: python run.py")
    print()
    
    print("📊 Langfuse Dashboard:")
    print("-" * 80)
    print("  • View traces: https://cloud.langfuse.com")
    print("  • Monitor sessions, feedback, and metrics")
    print("  • Check alert status and anomaly detection results")
    print()
    
    print("🔍 Testing Commands:")
    print("-" * 80)
    print("  • Run unit tests: pytest tests/unit/ -v")
    print("  • Run integration tests: pytest tests/integration/ -v")
    print("  • Test with coverage: pytest tests/ --cov=src")
    print()
    
    print("📝 Configuration Files:")
    print("-" * 80)
    print(f"  • Environment: {Path(__file__).parent / '.env'}")
    print(f"  • Alert rules: {Path(__file__).parent / 'config' / 'alerts.yaml'}")
    print(f"  • Alert example: {Path(__file__).parent / 'config' / 'alerts.yaml.example'}")
    print()
    
    print("💡 Tips:")
    print("-" * 80)
    print("  • Press Ctrl+C to stop the server")
    print("  • Server logs will show tool invocations and Langfuse traces")
    print("  • Use MCP Inspector to interactively test all tools")
    print("  • Check Langfuse dashboard to see real-time observability data")
    print()
    print("=" * 80)
    print()


def print_error_help(error: Exception):
    """Print helpful error message with solutions."""
    print()
    print("=" * 80)
    print("❌ Server failed to start")
    print("=" * 80)
    print()
    print(f"Error: {type(error).__name__}: {error}")
    print()
    print("🔍 Common solutions:")
    print()
    
    error_msg = str(error).lower()
    
    if "no module named" in error_msg:
        print("1️⃣  Missing Python module")
        print("   Solution: uv sync")
        print("   Or: pip install -r requirements.txt")
        print()
    
    if "langfuse" in error_msg or "api" in error_msg:
        print("2️⃣  Langfuse API connection failed")
        print("   Solution: Check your .env file")
        print("   - LANGFUSE_PUBLIC_KEY should start with 'pk-lf-'")
        print("   - LANGFUSE_SECRET_KEY should start with 'sk-lf-'")
        print("   - LANGFUSE_HOST should be 'https://cloud.langfuse.com'")
        print()
    
    if "permission" in error_msg or "access" in error_msg:
        print("3️⃣  Permission denied")
        print("   Solution: Check file permissions")
        print("   Or run with appropriate user privileges")
        print()
    
    print("💡 Need more help? Check:")
    print("   - docs/ directory for documentation")
    print("   - README.md for quick start guide")
    print("   - https://langfuse.com/docs for Langfuse documentation")
    print()
    print("=" * 80)


def main():
    """Run the MCP server with proper Python path configuration and diagnostics."""
    try:
        # Add project root to Python path to resolve 'src' imports
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        # Print startup banner
        print_banner()
        
        # Run pre-flight checks
        checks_passed = True
        checks_passed &= check_env_file()
        checks_passed &= check_dependencies()
        checks_passed &= check_project_structure()
        
        if not checks_passed:
            print("⚠️  Some checks failed. You can still try to start the server,")
            print("   but it may not work correctly.")
            print()
            response = input("Continue anyway? (y/N): ")
            if response.lower() != "y":
                print("\n👋 Startup cancelled.")
                sys.exit(1)
            print()
        
        # Show configuration
        show_config_info()
        
        # Print startup info
        print_startup_info()
        
        # Print access guide
        print_access_guide()
        
        # Import and run the server
        print("🚀 Launching MCP Server...\n")
        from src.server import main as server_main
        
        server_main()
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print_error_help(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
