"""CLI entry point."""
import sys

from skill_observability_toolkit.cli.init import init_command
from skill_observability_toolkit.cli.validate import validate_command


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m skill_observability_toolkit [init|validate]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        init_command()
    elif command == "validate":
        validate_command()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
