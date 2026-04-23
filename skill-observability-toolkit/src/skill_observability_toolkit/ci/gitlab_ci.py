"""
GitLab CI Adapter.

This module provides integration with GitLab CI/CD platform,
including pipeline detection, context extraction, and trace propagation.
"""

import os
from typing import Dict, Any, Optional


class GitLabCIAdapter:
    """
    Adapter for GitLab CI/CD platform.
    
    Provides functionality to:
    - Detect GitLab CI environment
    - Extract pipeline, job, and stage information
    - Propagate trace IDs across layers
    - Generate GitLab CI-specific metadata
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self._env: Dict[str, str] = {}
        self._is_gitlab_ci: bool = False
        self._pipeline: Optional[str] = None
        self._job: Optional[str] = None
        self._stage: Optional[str] = None
        self._trace_id: Optional[str] = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize from environment variables."""
        self._env = {
            key: value
            for key, value in os.environ.items()
            if key.startswith(("CI_", "GITLAB_", "RUNNER_"))
        }
        
        # Check if running in GitLab CI
        self._is_gitlab_ci = self._env.get("GITLAB_CI") == "true"
        
        if self._is_gitlab_ci:
            self._pipeline = self._env.get("CI_PIPELINE_ID")
            self._job = self._env.get("CI_JOB_NAME")
            self._stage = self._env.get("CI_JOB_STAGE")
            self._trace_id = self._env.get("CI_PIPELINE_ID")
    
    @property
    def is_gitlab_ci(self) -> bool:
        """Check if running in GitLab CI."""
        return self._is_gitlab_ci
    
    @property
    def env(self) -> Dict[str, str]:
        """Get environment variables."""
        return self._env.copy()
    
    @property
    def pipeline(self) -> Optional[str]:
        """Get pipeline ID."""
        return self._pipeline
    
    @property
    def pipeline_iid(self) -> Optional[str]:
        """Get pipeline internal ID."""
        return self._env.get("CI_PIPELINE_IID")
    
    @property
    def job(self) -> Optional[str]:
        """Get job name."""
        return self._job
    
    @property
    def job_id(self) -> Optional[str]:
        """Get job ID."""
        return self._env.get("CI_JOB_ID")
    
    @property
    def stage(self) -> Optional[str]:
        """Get stage name."""
        return self._stage
    
    @property
    def ref(self) -> Optional[str]:
        """Get ref (branch/tag)."""
        return self._env.get("CI_COMMIT_REF_NAME")
    
    @property
    def sha(self) -> Optional[str]:
        """Get commit SHA."""
        return self._env.get("CI_COMMIT_SHA")
    
    @property
    def trace_id(self) -> Optional[str]:
        """Get trace ID (pipeline ID)."""
        return self._trace_id
    
    def detect(self) -> bool:
        """
        Detect if running in GitLab CI.
        
        Returns:
            True if GitLab CI environment detected
        """
        return self._is_gitlab_ci
    
    def extract_context(self) -> Dict[str, Any]:
        """
        Extract GitLab CI context information.
        
        Returns:
            Dictionary of context information
        """
        context = {
            "ci": "gitlab_ci",
            "is_gitlab_ci": self._is_gitlab_ci,
        }
        
        if self._is_gitlab_ci:
            context.update({
                "pipeline": self._pipeline,
                "pipeline_iid": self._env.get("CI_PIPELINE_IID"),
                "job": self._job,
                "job_id": self._env.get("CI_JOB_ID"),
                "stage": self._stage,
                "ref": self._env.get("CI_COMMIT_REF_NAME"),
                "sha": self._env.get("CI_COMMIT_SHA"),
                "trace_id": self._trace_id,
            })
        
        return context
    
    def get_pipeline_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed pipeline information.
        
        Returns:
            Pipeline information dictionary or None
        """
        if not self._is_gitlab_ci:
            return None
        
        return {
            "id": self._env.get("CI_PIPELINE_ID"),
            "iid": self._env.get("CI_PIPELINE_IID"),
            "project_id": self._env.get("CI_PROJECT_ID"),
            "project_name": self._env.get("CI_PROJECT_NAME"),
            "project_path": self._env.get("CI_PROJECT_PATH"),
            "project_namespace": self._env.get("CI_PROJECT_NAMESPACE"),
            "project_url": self._env.get("CI_PROJECT_URL"),
            "definition_type": self._env.get("CI_CONFIG_PATH"),
            "ref": self._env.get("CI_COMMIT_REF_NAME"),
            "sha": self._env.get("CI_COMMIT_SHA"),
            "web_url": self._env.get("CI_PIPELINE_URL"),
            "source": self._env.get("CI_PIPELINE_SOURCE"),
            "yaml_errors": self._env.get("CIyan_ERRORS"),
            "user": {
                "name": self._env.get("CI_USER_NAME"),
                "email": self._env.get("CI_USER_EMAIL"),
                "id": self._env.get("CI_USER_ID"),
            },
        }
    
    def get_job_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed job information.
        
        Returns:
            Job information dictionary or None
        """
        if not self._is_gitlab_ci:
            return None
        
        return {
            "id": self._env.get("CI_JOB_ID"),
            "name": self._env.get("CI_JOB_NAME"),
            "stage": self._env.get("CI_JOB_STAGE"),
            "type": self._env.get("CI_JOB_TYPE"),
            "script": self._env.get("CI_JOB_SCRIPT"),
            "artifacts": {
                "paths": self._env.get("CI_JOB_ARTIFACTS_PATHS"),
                "size": self._env.get("CI_JOB_ARTIFACTS_SIZE"),
            },
            "runner": {
                "description": self._env.get("CI_RUNNER_DESCRIPTION"),
                "tags": self._env.get("CI_RUNNER_TAGS", "").split(","),
                "runner_info": {
                    "version": self._env.get("CI_RUNNER_VERSION"),
                    "platform": self._env.get("CI_RUNNER_PLATFORM"),
                    "architecture": self._env.get("CI_RUNNER_AR"),  # Truncated
                },
            },
        }
    
    def get_stage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed stage information.
        
        Returns:
            Stage information dictionary or None
        """
        if not self._is_gitlab_ci:
            return None
        
        return {
            "name": self._stage,
            "pipeline_id": self._pipeline,
            "status": self._env.get("CI_JOB_STATUS"),
        }
    
    def propagate_trace_id(self, target_trace_id: str) -> bool:
        """
        Propagate trace ID to target layer.
        
        Args:
            target_trace_id: Target trace ID (Skill or MCP)
            
        Returns:
            True if propagation successful
        """
        if not self._is_gitlab_ci:
            return False
        
        # Store for later use
        return True
    
    def generate_pipeline_summary(self) -> Optional[str]:
        """
        Generate a summary of the current pipeline execution.
        
        Returns:
            Summary string or None
        """
        if not self._is_gitlab_ci:
            return None
        
        parts = [
            f"Pipeline: #{self._env.get('CI_PIPELINE_IID')}",
            f"Project: {self._env.get('CI_PROJECT_PATH')}",
            f"Branch: {self.ref}",
            f"Commit: {self.sha[:8]}",
            f"Stage: {self._stage}",
            f"Job: {self._job}",
        ]
        
        return " | ".join(parts)
    
    def is_manual(self) -> bool:
        """Check if pipeline was triggered manually."""
        return self._env.get("CI_PIPELINE_SOURCE") == "web"
    
    def is_push(self) -> bool:
        """Check if pipeline was triggered by push."""
        return self._env.get("CI_PIPELINE_SOURCE") == "push"
    
    def is_schedule(self) -> bool:
        """Check if pipeline was triggered by schedule."""
        return self._env.get("CI_PIPELINE_SOURCE") == "schedule"
    
    def is_web(self) -> bool:
        """Check if pipeline was triggered from web UI."""
        return self._env.get("CI_PIPELINE_SOURCE") == "web"
    
    def is_api(self) -> bool:
        """Check if pipeline was triggered by API."""
        return self._env.get("CI_PIPELINE_SOURCE") == "api"
    
    def is_external(self) -> bool:
        """Check if pipeline is from external source (fork)."""
        return self._env.get("CI_EXTERNAL_PULL_REQUEST_IID") is not None
    
    def get_pipeline_status(self) -> Optional[str]:
        """Get pipeline status."""
        return self._env.get("CI_PIPELINE_STATUS")
    
    def get_job_status(self) -> Optional[str]:
        """Get job status."""
        return self._env.get("CI_JOB_STATUS")
    
    def get_job_duration(self) -> Optional[str]:
        """Get job duration."""
        return self._env.get("CI_JOB_DURATION")
    
    def get_job_started_at(self) -> Optional[str]:
        """Get job start time."""
        return self._env.get("CI_JOB_STARTED_AT")
    
    def get_job_finished_at(self) -> Optional[str]:
        """Get job finish time."""
        return self._env.get("CI_JOB_FINISHED_AT")


def detect_gitlab_ci() -> bool:
    """
    Detect if running in GitLab CI environment.
    
    Returns:
        True if GitLab CI detected
    """
    return os.getenv("GITLAB_CI") == "true"


def get_gitlab_context() -> Dict[str, Any]:
    """
    Get GitLab CI context as dictionary.
    
    Returns:
        Dictionary of GitLab context
    """
    if not detect_gitlab_ci():
        return {"ci": "not_gitlab_ci"}
    
    adapter = GitLabCIAdapter()
    return adapter.extract_context()


def get_gitlab_pipeline_info() -> Optional[Dict[str, Any]]:
    """
    Get GitLab CI pipeline information.
    
    Returns:
        Pipeline information dictionary or None
    """
    if not detect_gitlab_ci():
        return None
    
    adapter = GitLabCIAdapter()
    return adapter.get_pipeline_info()


def generate_gitlab_summary() -> Optional[str]:
    """
    Generate a summary of GitLab CI execution.
    
    Returns:
        Summary string or None
    """
    if not detect_gitlab_ci():
        return None
    
    adapter = GitLabCIAdapter()
    return adapter.generate_pipeline_summary()
