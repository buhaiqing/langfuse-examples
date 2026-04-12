"""
Configuration settings for Langfuse Smart Customer Service System
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Langfuse Configuration
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Environment Settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
RELEASE_VERSION = os.getenv("RELEASE_VERSION", "v1.0.0")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Tracing Configuration
ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Performance Settings
LANGFUSE_FLUSH_AT = int(os.getenv("LANGFUSE_FLUSH_AT", "50"))
LANGFUSE_FLUSH_INTERVAL = int(os.getenv("LANGFUSE_FLUSH_INTERVAL", "5"))


# Validate required configuration
def validate_config():
    """Validate that required configuration is present"""
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        raise ValueError(
            "Langfuse credentials not configured. "
            "Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env file"
        )
