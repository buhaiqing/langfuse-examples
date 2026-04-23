"""
Build Profiler.

This module provides profiling capabilities for CI/CD builds,
tracking performance metrics and identifying optimization opportunities.
"""

import time
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class StepProfile:
    """Profile data for a single CI step."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def stop(self):
        """Stop profiling this step."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "completed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class BuildProfile:
    """Complete profile for a CI build."""
    build_id: str
    build_number: Optional[int] = None
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    workflow: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_duration_ms: Optional[float] = None
    steps: List[StepProfile] = field(default_factory=list)
    status: str = "in_progress"
    environment: Dict[str, str] = field(default_factory=dict)
    
    def start(self):
        """Mark build as started."""
        self.started_at = time.time()
    
    def complete(self, status: str = "success"):
        """Mark build as completed."""
        self.completed_at = time.time()
        self.total_duration_ms = (self.completed_at - self.started_at) * 1000
        self.status = status
    
    def add_step(self, step: StepProfile):
        """Add a step to the build."""
        self.steps.append(step)
    
    def get_slow_steps(self, threshold_ms: float = 5000.0) -> List[StepProfile]:
        """Get steps that exceeded the duration threshold."""
        return [
            step for step in self.steps
            if step.duration_ms and step.duration_ms > threshold_ms
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Calculate build statistics."""
        durations = [
            step.duration_ms for step in self.steps
            if step.duration_ms is not None
        ]
        
        if not durations:
            return {
                "total_duration_ms": self.total_duration_ms,
                "step_count": len(self.steps),
                "slow_step_count": 0,
            }
        
        return {
            "total_duration_ms": self.total_duration_ms,
            "step_count": len(self.steps),
            "slow_step_count": len(self.get_slow_steps()),
            "mean_duration_ms": statistics.mean(durations),
            "median_duration_ms": statistics.median(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "std_deviation_ms": statistics.stdev(durations) if len(durations) > 1 else 0,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "build_id": self.build_id,
            "build_number": self.build_number,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "workflow": self.workflow,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_duration_ms": self.total_duration_ms,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "stats": self.get_stats(),
            "environment": self.environment,
        }


class BuildProfiler:
    """
    Profiler for CI/CD builds.
    
    Tracks timing, memory, and CPU usage of CI pipeline steps,
    identifies performance bottlenecks, and generates optimization reports.
    """
    
    def __init__(
        self,
        build_id: Optional[str] = None,
        threshold_ms: float = 5000.0,
    ):
        """
        Initialize the profiler.
        
        Args:
            build_id: Optional build ID (auto-generated if None)
            threshold_ms: Duration threshold for slow steps (default: 5s)
        """
        self.build_id = build_id or f"build_{int(time.time())}"
        self.threshold_ms = threshold_ms
        
        self._build_profile: Optional[BuildProfile] = None
        self._current_step: Optional[StepProfile] = None
        self._start_time: Optional[float] = None
    
    def start_build(
        self,
        build_number: Optional[int] = None,
        commit_sha: Optional[str] = None,
        branch: Optional[str] = None,
        workflow: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> "BuildProfiler":
        """
        Start profiling a new build.
        
        Args:
            build_number: Optional build number
            commit_sha: Optional commit SHA
            branch: Optional branch name
            workflow: Optional workflow name
            environment: Optional environment variables
            
        Returns:
            Self for method chaining
        """
        self._start_time = time.time()
        
        self._build_profile = BuildProfile(
            build_id=self.build_id,
            build_number=build_number,
            commit_sha=commit_sha,
            branch=branch,
            workflow=workflow,
        )
        self._build_profile.environment = environment or {}
        self._build_profile.start()
        
        return self
    
    def start_step(
        self,
        step_name: str,
        step_type: str = "unknown",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "BuildProfiler":
        """
        Start profiling a new CI step.
        
        Args:
            step_name: Name of the step
            step_type: Type of step (build, test, deploy, etc.)
            tags: Optional tags for categorization
            metadata: Optional metadata
            
        Returns:
            Self for method chaining
        """
        self._current_step = StepProfile(
            name=step_name,
            start_time=time.time(),
            tags=tags or [],
            metadata=metadata or {},
        )
        
        if self._build_profile:
            self._build_profile.add_step(self._current_step)
        
        return self
    
    def end_step(
        self,
        status: str = "success",
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        output: Optional[Dict[str, Any]] = None,
    ) -> "BuildProfiler":
        """
        End profiling the current CI step.
        
        Args:
            status: Step status (success, failure, skipped)
            memory_mb: Optional peak memory usage in MB
            cpu_percent: Optional average CPU usage percentage
            output: Optional step output data
            
        Returns:
            Self for method chaining
        """
        if self._current_step:
            self._current_step.status = status
            self._current_step.memory_mb = memory_mb
            self._current_step.cpu_percent = cpu_percent
            if output:
                self._current_step.metadata["output"] = output
            self._current_step.stop()
        
        return self
    
    def complete_build(self, status: str = "success") -> BuildProfile:
        """
        Complete the build profiling.
        
        Args:
            status: Build status
            
        Returns:
            Complete build profile
        """
        if self._build_profile:
            self._build_profile.complete(status)
        
        return self._build_profile
    
    def get_slow_steps(self) -> List[StepProfile]:
        """Get steps that exceeded the threshold."""
        if self._build_profile:
            return self._build_profile.get_slow_steps(self.threshold_ms)
        return []
    
    def get_profile(self) -> Optional[BuildProfile]:
        """Get the current build profile."""
        return self._build_profile
    
    def print_report(self, profile: Optional[BuildProfile] = None) -> str:
        """
        Generate a performance report.
        
        Args:
            profile: Build profile (uses current if None)
            
        Returns:
            Formatted report string
        """
        profile = profile or self._build_profile
        if not profile:
            return "No build profile available."
        
        lines = []
        lines.append("=" * 60)
        lines.append("CI/CD BUILD PERFORMANCE REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Build info
        lines.append(f"Build ID: {profile.build_id}")
        if profile.build_number:
            lines.append(f"Build Number: {profile.build_number}")
        if profile.commit_sha:
            lines.append(f"Commit: {profile.commit_sha[:8]}")
        if profile.branch:
            lines.append(f"Branch: {profile.branch}")
        if profile.workflow:
            lines.append(f"Workflow: {profile.workflow}")
        
        lines.append(f"Status: {profile.status}")
        lines.append(f"Duration: {profile.total_duration_ms:.2f} ms")
        lines.append("")
        
        # Statistics
        stats = profile.get_stats()
        lines.append("STEP STATISTICS:")
        lines.append(f"  Total Steps: {stats['step_count']}")
        lines.append(f"  Slow Steps: {stats['slow_step_count']}")
        
        if stats.get("mean_duration_ms"):
            lines.append(f"  Mean Duration: {stats['mean_duration_ms']:.2f} ms")
            lines.append(f"  Median Duration: {stats['median_duration_ms']:.2f} ms")
            lines.append(f"  Max Duration: {stats['max_duration_ms']:.2f} ms")
            lines.append(f"  Min Duration: {stats['min_duration_ms']:.2f} ms")
        
        lines.append("")
        
        # Slow steps
        slow_steps = profile.get_slow_steps(self.threshold_ms)
        if slow_steps:
            lines.append("SLOW STEPS (> {:.0f} ms):".format(self.threshold_ms))
            for i, step in enumerate(slow_steps, 1):
                lines.append(f"  {i}. {step.name}: {step.duration_ms:.2f} ms")
            lines.append("")
        
        # Step details
        lines.append("ALL STEPS:")
        for i, step in enumerate(profile.steps, 1):
            duration_line = f"{step.duration_ms:.2f} ms" if step.duration_ms else "running"
            status_icon = "✅" if step.status == "success" else "❌" if step.status == "failure" else "⚠️"
            lines.append(f"  {i}. {status_icon} {step.name}: {duration_line}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class BuildProfilerManager:
    """
    Manager for multiple build profilers.
    
    Supports tracking multiple builds and comparing performance over time.
    """
    
    def __init__(
        self,
        max_builds: int = 100,
        threshold_ms: float = 5000.0,
    ):
        """
        Initialize the manager.
        
        Args:
            max_builds: Maximum number of builds to retain
            threshold_ms: Threshold for slow steps
        """
        self.max_builds = max_builds
        self.threshold_ms = threshold_ms
        
        self._builds: List[BuildProfile] = []
        self._current_profiler: Optional[BuildProfiler] = None
    
    def start_profiler(
        self,
        build_id: Optional[str] = None,
        **kwargs,
    ) -> BuildProfiler:
        """
        Start a new build profiler.
        
        Args:
            build_id: Optional build ID
            **kwargs: Arguments passed to BuildProfiler
            
        Returns:
            New BuildProfiler instance
        """
        profiler = BuildProfiler(
            build_id=build_id,
            threshold_ms=self.threshold_ms,
        )
        
        profiler.start_build(**kwargs)
        self._current_profiler = profiler
        
        return profiler
    
    def end_profiler(self) -> Optional[BuildProfile]:
        """
        End the current profiler and store the profile.
        
        Returns:
            Complete build profile or None
        """
        if self._current_profiler:
            profile = self._current_profiler.complete_build()
            self._builds.append(profile)
            
            # Trim old builds
            if len(self._builds) > self.max_builds:
                self._builds = self._builds[-self.max_builds:]
            
            self._current_profiler = None
            return profile
        
        return None
    
    def get_build(self, build_id: str) -> Optional[BuildProfile]:
        """Get a specific build profile."""
        for profile in self._builds:
            if profile.build_id == build_id:
                return profile
        return None
    
    def get_latest_build(self) -> Optional[BuildProfile]:
        """Get the most recent build profile."""
        return self._builds[-1] if self._builds else None
    
    def get_comparison(
        self,
        count: int = 5,
    ) -> Dict[str, Any]:
        """
        Compare recent builds.
        
        Args:
            count: Number of builds to compare
            
        Returns:
            Comparison statistics
        """
        recent_builds = self._builds[-count:] if len(self._builds) > count else self._builds
        
        if not recent_builds:
            return {"error": "No builds to compare"}
        
        total_durations = [b.total_duration_ms for b in recent_builds if b.total_duration_ms]
        
        if not total_durations:
            return {"error": "No duration data"}
        
        return {
            "builds_compared": len(recent_builds),
            "mean_duration_ms": statistics.mean(total_durations),
            "median_duration_ms": statistics.median(total_durations),
            "max_duration_ms": max(total_durations),
            "min_duration_ms": min(total_durations),
            "improvement_percent": self._calculate_improvement(total_durations),
        }
    
    def _calculate_improvement(self, durations: List[float]) -> float:
        """Calculate improvement percentage between first and last builds."""
        if len(durations) < 2:
            return 0.0
        
        first = durations[0]
        last = durations[-1]
        
        if first == 0:
            return 0.0
        
        return ((first - last) / first) * 100
    
    def print_comparison_report(self, count: int = 5) -> str:
        """Print comparison report for recent builds."""
        comparison = self.get_comparison(count)
        
        lines = []
        lines.append("=" * 60)
        lines.append("BUILD PERFORMANCE COMPARISON")
        lines.append("=" * 60)
        lines.append("")
        
        if "error" in comparison:
            lines.append(f"Error: {comparison['error']}")
        else:
            lines.append(f"Builds Compared: {comparison['builds_compared']}")
            lines.append(f"Mean Duration: {comparison['mean_duration_ms']:.2f} ms")
            lines.append(f"Median Duration: {comparison['median_duration_ms']:.2f} ms")
            lines.append(f"Max Duration: {comparison['max_duration_ms']:.2f} ms")
            lines.append(f"Min Duration: {comparison['min_duration_ms']:.2f} ms")
            lines.append(f"Improvement: {comparison['improvement_percent']:.2f}%")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
