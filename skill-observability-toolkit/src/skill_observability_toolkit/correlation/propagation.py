"""
Cross-Layer Trace ID Propagation.

This module provides trace ID propagation across CI → Skill → MCP layers,
ensuring end-to-end correlation of traces.
"""

import os
from typing import Optional, Dict, Any

from skill_observability_toolkit.langfuse_integration.context import (
    get_trace_id as get_skill_trace_id,
    set_trace_id as set_skill_trace_id,
    get_parent_trace_id,
)
from skill_observability_toolkit.ci.context import (
    get_ci_trace_id,
    set_ci_trace_id,
    propagate_ci_to_skill as ci_propagate,
)
from skill_observability_toolkit.ci.decorators import get_ci_platform


class TracePropagator:
    """
    Propagate trace IDs across CI → Skill → MCP layers.
    
    Ensures that traces from different layers can be correlated
    using parent-child relationships.
    """
    
    def __init__(self):
        """Initialize the propagator."""
        self._mcp_trace_context: Dict[str, Any] = {}
    
    def propagate_ci_to_skill(
        self,
        ci_trace_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Propagate CI trace ID to Skill layer.
        
        Args:
            ci_trace_id: CI trace ID (if None, uses current context)
            
        Returns:
            Skill trace ID
        """
        if not ci_trace_id:
            ci_trace_id = get_ci_trace_id()
        
        if not ci_trace_id:
            return None
        
        # Get or create skill trace ID
        skill_trace_id = get_skill_trace_id()
        
        if not skill_trace_id:
            # Generate skill trace ID from CI trace ID
            skill_trace_id = f"skill_{ci_trace_id}"
            set_skill_trace_id(skill_trace_id)
        
        # Set parent trace ID for correlation
        from skill_observability_toolkit.langfuse_integration.context import (
            set_parent_trace_id,
        )
        set_parent_trace_id(ci_trace_id)
        
        return skill_trace_id
    
    def propagate_skill_to_mcp(
        self,
        skill_trace_id: Optional[str] = None,
        mcp_trace_prefix: str = "mcp",
    ) -> Optional[str]:
        """
        Propagate Skill trace ID to MCP layer.
        
        Args:
            skill_trace_id: Skill trace ID (if None, uses current context)
            mcp_trace_prefix: Prefix for MCP trace ID
            
        Returns:
            MCP trace ID
        """
        if not skill_trace_id:
            skill_trace_id = get_skill_trace_id()
        
        if not skill_trace_id:
            return None
        
        # Generate MCP trace ID from Skill trace ID
        mcp_trace_id = f"{mcp_trace_prefix}_{skill_trace_id[-8:]}"
        
        # Store for MCP layer
        self._mcp_trace_context["trace_id"] = mcp_trace_id
        self._mcp_trace_context["skill_trace_id"] = skill_trace_id
        
        return mcp_trace_id
    
    def propagate_ci_to_mcp(
        self,
        ci_trace_id: Optional[str] = None,
        mcp_trace_prefix: str = "mcp",
    ) -> Optional[str]:
        """
        Propagate CI trace ID directly to MCP layer (skips Skill layer).
        
        Args:
            ci_trace_id: CI trace ID (if None, uses current context)
            mcp_trace_prefix: Prefix for MCP trace ID
            
        Returns:
            MCP trace ID
        """
        if not ci_trace_id:
            ci_trace_id = get_ci_trace_id()
        
        if not ci_trace_id:
            return None
        
        # Use part of CI trace ID for MCP
        mcp_trace_id = f"{mcp_trace_prefix}_{ci_trace_id[-8:]}"
        
        self._mcp_trace_context["trace_id"] = mcp_trace_id
        self._mcp_trace_context["ci_trace_id"] = ci_trace_id
        
        return mcp_trace_id
    
    def create_trace_chain(
        self,
        ci_trace_id: Optional[str] = None,
        skill_trace_id: Optional[str] = None,
        mcp_trace_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create complete trace chain ID mapping.
        
        Args:
            ci_trace_id: CI trace ID
            skill_trace_id: Skill trace ID (optional)
            mcp_trace_id: MCP trace ID (optional)
            
        Returns:
            Dictionary with all trace IDs
        """
        chain = {}
        
        # Set CI trace ID if provided
        if ci_trace_id:
            set_ci_trace_id(ci_trace_id)
            chain["ci_trace_id"] = ci_trace_id
        
        # Propagate to Skill
        if ci_trace_id:
            skill_trace_id = self.propagate_ci_to_skill(ci_trace_id)
            if skill_trace_id:
                chain["skill_trace_id"] = skill_trace_id
        
        # Propagate to MCP
        if skill_trace_id or ci_trace_id:
            mcp_trace_id = self.propagate_skill_to_mcp(
                skill_trace_id,
                mcp_trace_prefix="mcp"
            )
            if mcp_trace_id:
                chain["mcp_trace_id"] = mcp_trace_id
        
        return chain
    
    def get_trace_context(self) -> Dict[str, Optional[str]]:
        """
        Get current trace context across all layers.
        
        Returns:
            Dictionary with trace IDs from all layers
        """
        return {
            "ci_trace_id": get_ci_trace_id(),
            "skill_trace_id": get_skill_trace_id(),
            "parent_trace_id": get_parent_trace_id(),
            "mcp_trace_id": self._mcp_trace_context.get("trace_id"),
        }
    
    def clear_context(self):
        """Clear all trace contexts."""
        from skill_observability_toolkit.langfuse_integration.context import (
            clear_trace_context,
        )
        
        clear_trace_context()
        self._mcp_trace_context = {}


# Global propagator instance
_propagator = TracePropagator()


def propagate_ci_to_skill(
    ci_trace_id: Optional[str] = None,
) -> Optional[str]:
    """
    Propagate CI trace ID to Skill layer (convenience function).
    
    Args:
        ci_trace_id: CI trace ID
        
    Returns:
        Skill trace ID
    """
    return _propagator.propagate_ci_to_skill(ci_trace_id)


def propagate_skill_to_mcp(
    skill_trace_id: Optional[str] = None,
) -> Optional[str]:
    """
    Propagate Skill trace ID to MCP layer (convenience function).
    
    Args:
        skill_trace_id: Skill trace ID
        
    Returns:
        MCP trace ID
    """
    return _propagator.propagate_skill_to_mcp(skill_trace_id)


def propagate_ci_to_mcp(
    ci_trace_id: Optional[str] = None,
) -> Optional[str]:
    """
    Propagate CI trace ID directly to MCP layer (convenience function).
    
    Args:
        ci_trace_id: CI trace ID
        
    Returns:
        MCP trace ID
    """
    return _propagator.propagate_ci_to_mcp(ci_trace_id)


def create_trace_chain(
    ci_trace_id: Optional[str] = None,
    skill_trace_id: Optional[str] = None,
    mcp_trace_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create complete trace chain (convenience function).
    
    Args:
        ci_trace_id: CI trace ID
        skill_trace_id: Skill trace ID
        mcp_trace_id: MCP trace ID
        
    Returns:
        Dictionary with all trace IDs
    """
    return _propagator.create_trace_chain(
        ci_trace_id, skill_trace_id, mcp_trace_id
    )


def get_trace_context() -> Dict[str, Optional[str]]:
    """
    Get current trace context (convenience function).
    
    Returns:
        Dictionary with trace IDs from all layers
    """
    return _propagator.get_trace_context()


def clear_trace_context():
    """Clear all trace contexts (convenience function)."""
    _propagator.clear_context()


def detect_and_propagate_all() -> Dict[str, str]:
    """
    Detect current CI platform and propagate trace IDs automatically.
    
    Returns:
        Dictionary with all trace IDs
    """
    from skill_observability_toolkit.ci.decorators import (
        is_github_actions,
        is_gitlab_ci,
        get_ci_context,
    )
    
    ci_context = get_ci_context()
    
    if not ci_context.get("ci"):
        return {"error": "No CI environment detected"}
    
    trace_chain = {}
    
    # Get CI trace ID
    ci_trace_id = ci_context.get("trace_id")
    
    if ci_trace_id:
        # Propagate to Skill
        skill_trace_id = propagate_ci_to_skill(ci_trace_id)
        if skill_trace_id:
            trace_chain["skill_trace_id"] = skill_trace_id
        
        # Propagate to MCP
        mcp_trace_id = propagate_skill_to_mcp(skill_trace_id)
        if mcp_trace_id:
            trace_chain["mcp_trace_id"] = mcp_trace_id
    
    return trace_chain
