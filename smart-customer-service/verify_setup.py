"""
Quick verification script to check project structure
"""

import os
import sys


def verify_structure():
    """Verify project structure is correct"""
    print("Verifying project structure...")
    print("-" * 60)

    required_files = [
        "config/settings.py",
        "core/langfuse_client.py",
        "core/tracing.py",
        "core/scoring.py",
        "utils/data_masking.py",
        "utils/helpers.py",
        "modules/intent_recognition.py",
        "modules/rag_knowledge.py",
        "modules/tool_calling.py",
        "modules/dialogue_manager.py",
        "modules/escalation.py",
        "main.py",
        "examples/basic_tracing.py",
        "requirements.txt",
        ".env.example",
        "README.md",
    ]

    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
            all_exist = False

    print("-" * 60)

    if all_exist:
        print("✅ All required files present!")
    else:
        print("❌ Some files are missing.")

    return all_exist


def verify_dependencies():
    """Check if dependencies can be imported"""
    print("\nChecking Python dependencies...")
    print("-" * 60)

    dependencies = [
        ("langfuse", "Langfuse SDK"),
        ("langchain_openai", "LangChain OpenAI"),
        ("dotenv", "python-dotenv"),
    ]

    all_installed = True
    for package, name in dependencies:
        try:
            __import__(package.split(".")[0])
            print(f"✓ {name} ({package})")
        except ImportError:
            print(f"✗ {name} ({package}) - not installed")
            all_installed = False

    print("-" * 60)

    if all_installed:
        print("✅ All dependencies installed!")
    else:
        print("⚠️  Some dependencies missing. Run: pip install -r requirements.txt")

    return all_installed


if __name__ == "__main__":
    print("=" * 60)
    print("Langfuse Smart Customer Service - Project Verification")
    print("=" * 60)
    print()

    structure_ok = verify_structure()
    deps_ok = verify_dependencies()

    print()
    print("=" * 60)

    if structure_ok and deps_ok:
        print("✅ Project is ready!")
        print()
        print("Next steps:")
        print("  1. Copy .env.example to .env and add your API keys")
        print("  2. Run: python examples/basic_tracing.py")
        print("  3. Run: python main.py")
        sys.exit(0)
    else:
        print("⚠️  Please fix the issues above.")
        sys.exit(1)
