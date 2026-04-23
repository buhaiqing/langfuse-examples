"""
CI/CD Trace Context Management.

This module provides context management for CI/CD traces,
including cross-layer trace ID propagation.
"""

import os
from contextvars import ContextVar
from typing import Optional, Dict, Any

# CI trace context
_ci_trace_id_context: ContextVar[Optional[str]] = ContextVar(
    "ci_trace_id", default=None
)

# CI stage context
_ci_stage_context: ContextVar[Optional[str]] = ContextVar(
    "ci_stage", default=None
)

# Current step context
_current_step_context: ContextVar[Optional[str]] = ContextVar(
    "ci_step", default=None
)


def set_ci_trace_id(trace_id: str) -> None:
    """Set the CI trace ID."""
    _ci_trace_id_context.set(trace_id)


def get_ci_trace_id() -> Optional[str]:
    """Get the CI trace ID."""
    return _ci_trace_id_context.get()


def generate_ci_trace_id(prefix: str = "ci_build") -> str:
    """
    Generate a new CI trace ID.
    
    Args:
        prefix: Prefix for trace ID
        
    Returns:
        Generated trace ID
    """
    import uuid
    trace_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
    set_ci_trace_id(trace_id)
    return trace_id


def set_ci_stage(stage_name: str) -> None:
    """Set the current CI stage."""
    _ci_stage_context.set(stage_name)


def get_ci_stage() -> Optional[str]:
    """Get the current CI stage."""
    return _ci_stage_context.get()


def set_current_step(step_name: str) -> None:
    """Set the current CI step."""
    _current_step_context.set(step_name)


def get_current_step() -> Optional[str]:
    """Get the current CI step."""
    return _current_step_context.get()


def clear_ci_context() -> None:
    """Clear all CI context variables."""
    _ci_trace_id_context.set(None)
    _ci_stage_context.set(None)
    _current_step_context.set(None)


def get_ci_context() -> Dict[str, Any]:
    """
    Get full CI context.
    
    Returns:
        Dictionary containing all CI context variables
    """
    return {
        "trace_id": get_ci_trace_id(),
        "stage": get_ci_stage(),
        "step": get_current_step(),
    }


def set_ci_context_from_env() -> Dict[str, Any]:
    """
    Set CI context from environment variables.
    
    Returns:
        Dictionary of set context variables
    """
    context = {}
    
    # GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        run_id = os.getenv("GITHUB_RUN_ID")
        if run_id:
            set_ci_trace_id(run_id)
            context["trace_id"] = run_id
        
        workflow = os.getenv("GITHUB_WORKFLOW")
        if workflow:
            context["workflow"] = workflow
        
        job = os.getenv("GITHUB_JOB")
        if job:
            context["job"] = job
    
    # GitLab CI
    elif os.getenv("GITLAB_CI") == "true":
        pipeline_id = os.getenv("CI_PIPELINE_ID")
        if pipeline_id:
            set_ci_trace_id(pipeline_id)
            context["trace_id"] = pipeline_id
        
        stage = os.getenv("CI_JOB_STAGE")
        if stage:
            set_ci_stage(stage)
            context["stage"] = stage
        
        job = os.getenv("CI_JOB_NAME")
        if job:
            set_current_step(job)
            context["step"] = job
    
    return context


class CIContextManager:
    """Context manager for CI context."""
    
    def __init__(
        self,
        trace_id: Optional[str] = None,
        stage: Optional[str] = None,
        step: Optional[str] = None,
    ):
        self.trace_id = trace_id
        self.stage = stage
        self.step = step
        self._tokens = []
        self._previous_context = {}
    
    def __enter__(self):
        """Enter context manager."""
        # Save previous context
        self._previous_context = get_ci_context()
        
        # Set new context
        if self.trace_id:
            self._tokens.append(_ci_trace_id_context.set(self.trace_id))
        if self.stage:
            self._tokens.append(_ci_stage_context.set(self.stage))
        if self.step:
            self._tokens.append(_current_step_context.set(self.step))
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and restore context."""
        # Restore previous context
        if self._previous_context.get("trace_id"):
            set_ci_trace_id(self._previous_context["trace_id"])
        if self._previous_context.get("stage"):
            set_ci_stage(self._previous_context["stage"])
        if self._previous_context.get("step"):
            set_current_step(self._previous_context["step"])
        
        self._previous_context = {}
        return False


def create_ci_context(
    trace_id: Optional[str] = None,
    stage: Optional[str] = None,
    step: Optional[str] = None,
) -> CIContextManager:
    """
    Create a CI context manager.
    
    Args:
        trace_id: CI trace ID
        stage: Stage name
        step: Step name
        
    Returns:
        CIContextManager instance
    """
    return CIContextManager(
        trace_id=trace_id,
        stage=stage,
        step=step,
    )


def propagate_ci_to_skill(
    ci_trace_id: Optional[str] = None,
) -> Optional[str]:
    """
    Propagate CI trace ID to Skill layer.
    
    Args:
        ci_trace_id: CI trace ID (if None, uses current context)
        
    Returns:
        Skill trace ID
    """
    from skill_observability_toolkit.langfuse_integration.context import (
        get_trace_id,
        set_trace_id,
    )
    
    if not ci_trace_id:
        ci_trace_id = get_ci_trace_id()
    
    if ci_trace_id:
        skill_trace_id = get_trace_id()
        if not skill_trace_id:
            skill_trace_id = f"skill_{ci_trace_id}"
            set_trace_id(skill_trace_id)
        
        return skill_trace_id
    
    return None


def create_cross_layer_context(
    ci_trace_id: str,
    skill_trace_id: Optional[str] = None,
    mcp_trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create cross-layer trace context.
    
    Args:
        ci_trace_id: CI trace ID
        skill_trace_id: Optional skill trace ID
        mcp_trace_id: Optional MCP trace ID
        
    Returns:
        Dictionary with all trace IDs
    """
    context = {
        "ci_trace_id": ci_trace_id,
        "skill_trace_id": skill_trace_id,
        "mcp_trace_id": mcp_trace_id,
    }
    
    # Set context
    set_ci_trace_id(ci_trace_id)
    
    if skill_trace_id:
        from skill_observability_toolkit.langfuse_integration.context import (
            set_trace_id,
        )
        set_trace_id(skill_trace_id)
    
    if mcp_trace_id:
        from skill_observability_toolkit.mcp.context import set_trace_id as mcp_set_id
        mcp_set_id(mcp_trace_id)
    
    return context
