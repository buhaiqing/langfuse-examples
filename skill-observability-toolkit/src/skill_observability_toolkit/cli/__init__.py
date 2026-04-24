"""
CLI: Main entry point for STOP Protocol tools.

This module provides the command-line interface for STOP Protocol tools:
- stop init: Initialize a new Skill project
- stop validate: Validate a skill.yaml manifest
- stop run: Run a Skill with tracing
- stop observe: Seamlessly add observability to existing Skills
"""

import typer

from .init import app as init_app
from .observe import app as observe_app
from .validate import app as validate_app

__all__ = ["init_app", "validate_app", "observe_app"]
