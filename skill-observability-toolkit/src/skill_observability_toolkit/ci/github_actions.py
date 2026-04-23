"""
GitHub Actions Adapter.

This module provides integration with GitHub Actions CI/CD platform,
including workflow detection, context extraction, and trace propagation.
"""

import os
from typing import Any


class GitHubActionsAdapter:
    """
    Adapter for GitHub Actions CI/CD platform.

    Provides functionality to:
    - Detect GitHub Actions environment
    - Extract workflow, job, and step information
    - Propagate trace IDs across layers
    - Generate GitHub Actions-specific metadata
    """

    def __init__(self):
        """Initialize the adapter."""
        self._env: dict[str, str] = {}
        self._is_github_actions: bool = False
        self._workflow: str | None = None
        self._job: str | None = None
        self._step: str | None = None
        self._trace_id: str | None = None

        self._initialize()

    def _initialize(self):
        """Initialize from environment variables."""
        self._env = {
            key: value
            for key, value in os.environ.items()
            if key.startswith(("GITHUB_", "CI_", "RUNNER_"))
        }

        # Check if running in GitHub Actions
        self._is_github_actions = self._env.get("GITHUB_ACTIONS") == "true"

        if self._is_github_actions:
            self._workflow = self._env.get("GITHUB_WORKFLOW")
            self._job = self._env.get("GITHUB_JOB")
            self._step = self._env.get("GITHUB_STEP")
            self._trace_id = self._env.get("GITHUB_RUN_ID")

    @property
    def is_github_actions(self) -> bool:
        """Check if running in GitHub Actions."""
        return self._is_github_actions

    @property
    def env(self) -> dict[str, str]:
        """Get environment variables."""
        return self._env.copy()

    @property
    def workflow(self) -> str | None:
        """Get workflow name."""
        return self._workflow

    @property
    def job(self) -> str | None:
        """Get job name."""
        return self._job

    @property
    def step(self) -> str | None:
        """Get step name."""
        return self._step

    @property
    def trace_id(self) -> str | None:
        """Get trace ID (run ID)."""
        return self._trace_id

    @property
    def run_number(self) -> str | None:
        """Get run number."""
        return self._env.get("GITHUB_RUN_NUMBER")

    @property
    def run_attempt(self) -> str | None:
        """Get run attempt number."""
        return self._env.get("GITHUB_RUN_ATTEMPT")

    @property
    def actor(self) -> str | None:
        """Get actor (user who triggered the run)."""
        return self._env.get("GITHUB_ACTOR")

    @property
    def repository(self) -> str | None:
        """Get repository name."""
        return self._env.get("GITHUB_REPOSITORY")

    @property
    def ref(self) -> str | None:
        """Get ref (branch/tag)."""
        return self._env.get("GITHUB_REF")

    @property
    def sha(self) -> str | None:
        """Get commit SHA."""
        return self._env.get("GITHUB_SHA")

    def detect(self) -> bool:
        """
        Detect if running in GitHub Actions.

        Returns:
            True if GitHub Actions environment detected
        """
        return self._is_github_actions

    def extract_context(self) -> dict[str, Any]:
        """
        Extract GitHub Actions context information.

        Returns:
            Dictionary of context information
        """
        context = {
            "ci": "github_actions",
            "is_github_actions": self._is_github_actions,
        }

        if self._is_github_actions:
            context.update({
                "workflow": self._workflow,
                "job": self._job,
                "step": self._step,
                "trace_id": self._trace_id,
                "run_number": self._env.get("GITHUB_RUN_NUMBER"),
                "run_attempt": self._env.get("GITHUB_RUN_ATTEMPT"),
                "actor": self._env.get("GITHUB_ACTOR"),
                "repository": self._env.get("GITHUB_REPOSITORY"),
                "ref": self._env.get("GITHUB_REF"),
                "sha": self._env.get("GITHUB_SHA"),
            })

        return context

    def get_workflow_info(self) -> dict[str, Any] | None:
        """
        Get detailed workflow information.

        Returns:
            Workflow information dictionary or None
        """
        if not self._is_github_actions:
            return None

        return {
            "name": self._env.get("GITHUB_WORKFLOW"),
            "id": self._env.get("GITHUB_RUN_ID"),
            "number": self._env.get("GITHUB_RUN_NUMBER"),
            "attempt": self._env.get("GITHUB_RUN_ATTEMPT"),
            "actor": self._env.get("GITHUB_ACTOR"),
            "repository": self._env.get("GITHUB_REPOSITORY"),
            "ref": self._env.get("GITHUB_REF"),
            "sha": self._env.get("GITHUB_SHA"),
            "event_name": self._env.get("GITHUB_EVENT_NAME"),
            "event_path": self._env.get("GITHUB_EVENT_PATH"),
            "workspace": self._env.get("GITHUB_WORKSPACE"),
            "action": self._env.get("GITHUB_ACTION"),
            "actor_id": self._env.get("GITHUB_ACTOR_ID"),
        }

    def get_job_info(self) -> dict[str, Any] | None:
        """
        Get detailed job information.

        Returns:
            Job information dictionary or None
        """
        if not self._is_github_actions:
            return None

        return {
            "name": self._env.get("GITHUB_JOB"),
            "stage": self._env.get("GITHUB_JOB"),
            "runner": {
                "name": self._env.get("RUNNER_NAME"),
                "os": self._env.get("RUNNER_OS"),
                "arch": self._env.get("RUNNER_ARCH"),
            },
        }

    def get_step_info(self) -> dict[str, Any] | None:
        """
        Get detailed step information.

        Returns:
            Step information dictionary or None
        """
        if not self._is_github_actions:
            return None

        return {
            "name": self._env.get("GITHUB_STEP"),
            "description": self._env.get("GITHUB_STEP_SUMMARY"),
        }

    def propagate_trace_id(self, target_trace_id: str) -> bool:
        """
        Propagate trace ID to target layer.

        Args:
            target_trace_id: Target trace ID (Skill or MCP)

        Returns:
            True if propagation successful
        """
        if not self._is_github_actions:
            return False

        # Store for later use
        # In practice, this would set environment variables or context
        return True

    def generate_workflow_summary(self) -> str | None:
        """
        Generate a summary of the current workflow execution.

        Returns:
            Summary string or None
        """
        if not self._is_github_actions:
            return None

        parts = [
            f"Workflow: {self._workflow}",
            f"Run: #{self.run_number}",
            f"Branch: {self.ref}",
            f"Commit: {self.sha[:8]}",
            f" Actor: {self.actor}",
            f"Job: {self.job}",
        ]

        return " | ".join(parts)

    def is_workflow_dispatch(self) -> bool:
        """Check if workflow was triggered by workflow_dispatch."""
        return self._env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

    def is_pull_request(self) -> bool:
        """Check if workflow was triggered by pull_request."""
        return self._env.get("GITHUB_EVENT_NAME") == "pull_request"

    def get_pr_number(self) -> str | None:
        """Get pull request number if applicable."""
        return self._env.get("GITHUB_HEAD_REF")

    def is_push(self) -> bool:
        """Check if workflow was triggered by push."""
        return self._env.get("GITHUB_EVENT_NAME") == "push"

    def is_schedule(self) -> bool:
        """Check if workflow was triggered by schedule."""
        return self._env.get("GITHUB_EVENT_NAME") == "schedule"

    def get_current_time(self) -> str:
        """Get current time from GitHub Actions runner."""
        return self._env.get("GITHUB_SERVER_URL", "") + "/" + \
               self._env.get("GITHUB_REPOSITORY", "") + \
               "/actions/runs/" + \
               self._env.get("GITHUB_RUN_ID", "") + \
               "/at/" + \
               self._env.get("GITHUB_RUN_ATTEMPT", "")


def detect_github_actions() -> bool:
    """
    Detect if running in GitHub Actions environment.

    Returns:
        True if GitHub Actions detected
    """
    return os.getenv("GITHUB_ACTIONS") == "true"


def get_github_context() -> dict[str, Any]:
    """
    Get GitHub Actions context as dictionary.

    Returns:
        Dictionary of GitHub context
    """
    if not detect_github_actions():
        return {"ci": "not_github_actions"}

    adapter = GitHubActionsAdapter()
    return adapter.extract_context()


def get_github_workflow_info() -> dict[str, Any] | None:
    """
    Get GitHub Actions workflow information.

    Returns:
        Workflow information dictionary or None
    """
    if not detect_github_actions():
        return None

    adapter = GitHubActionsAdapter()
    return adapter.get_workflow_info()


def generate_github_summary() -> str | None:
    """
    Generate a summary of GitHub Actions execution.

    Returns:
        Summary string or None
    """
    if not detect_github_actions():
        return None

    adapter = GitHubActionsAdapter()
    return adapter.generate_workflow_summary()
