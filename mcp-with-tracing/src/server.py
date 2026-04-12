"""
MCP Server entry point.
"""

from fastmcp import FastMCP

from src.observability import (
    init_observability,
    ObservabilityConfig,
    observe_tool,
    set_session_context,
)

mcp = FastMCP("MCP Langfuse Observability Server")


@mcp.tool()
@observe_tool(name="echo_tool")
def echo(message: str) -> str:
    """Echo back the input message."""
    return f"Echo: {message}"


@mcp.tool()
@observe_tool(name="calculate_tool")
def calculate(operation: str, a: float, b: float) -> float:
    """
    Perform a basic calculation.

    Args:
        operation: Operation type (add, subtract, multiply, divide).
        a: First operand.
        b: Second operand.

    Returns:
        Result of the operation.
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


@mcp.tool()
@observe_tool(name="greet_tool")
def greet(name: str, language: str = "en") -> str:
    """
    Generate a greeting.

    Args:
        name: Name to greet.
        language: Language code (en, es, fr).

    Returns:
        Greeting message.
    """
    greetings = {
        "en": f"Hello, {name}!",
        "es": f"¡Hola, {name}!",
        "fr": f"Bonjour, {name}!",
    }
    return greetings.get(language, f"Hello, {name}!")


def main():
    """Run the MCP server."""
    config = ObservabilityConfig()
    init_observability(config)
    mcp.run()


if __name__ == "__main__":
    main()
