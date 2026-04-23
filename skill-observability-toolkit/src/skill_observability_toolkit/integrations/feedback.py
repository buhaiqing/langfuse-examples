"""
Feedback System Integration.

This module provides integration with the feedback system from mcp-with-tracing.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FeedbackType(Enum):
    """Feedback type."""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    PRODUCT_SUGGESTION = "product_suggestion"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"


@dataclass
class Feedback:
    """Feedback instance."""
    id: str
    type: FeedbackType
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: 0)  # Will be set after
    trace_id: str | None = None
    user_id: str | None = None

    def __post_init__(self):
        """Set timestamp after init."""
        if self.timestamp == 0:
            import time
            self.timestamp = time.time()


class FeedbackCollector:
    """
    Collect and manage feedback.

    Provides functionality to:
    - Collect feedback from users
    - Store feedback
    - Analyze feedback
    - Export feedback
    """

    def __init__(self, storage_path: str | None = None):
        """
        Initialize the feedback collector.

        Args:
            storage_path: Path to feedback storage
        """
        self._feedback: list[Feedback] = []
        self._storage_path = storage_path

    def collect(
        self,
        feedback_type: FeedbackType,
        message: str,
        trace_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Feedback:
        """
        Collect feedback.

        Args:
            feedback_type: Type of feedback
            message: Feedback message
            trace_id: Associated trace ID
            user_id: User ID
            metadata: Additional metadata

        Returns:
            Created feedback instance
        """
        feedback = Feedback(
            id=self._generate_feedback_id(),
            type=feedback_type,
            message=message,
            trace_id=trace_id,
            user_id=user_id,
            metadata=metadata or {},
        )

        self._feedback.append(feedback)

        # Store feedback
        self._store_feedback(feedback)

        return feedback

    def _generate_feedback_id(self) -> str:
        """Generate unique feedback ID."""
        import uuid
        return f"feedback_{uuid.uuid4().hex[:8]}"

    def _store_feedback(self, feedback: Feedback) -> bool:
        """
        Store feedback.

        Args:
            feedback: Feedback to store

        Returns:
            True if stored successfully
        """
        # In-memory storage (already added to self._feedback in collect())
        # Optional file persistence if storage_path is configured
        if self._storage_path:
            try:
                import json
                from pathlib import Path
                
                storage_file = Path(self._storage_path) / f"{feedback.id}.json"
                storage_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(storage_file, 'w') as f:
                    json.dump({
                        "id": feedback.id,
                        "type": feedback.type.value,
                        "message": feedback.message,
                        "timestamp": feedback.timestamp,
                        "trace_id": feedback.trace_id,
                        "user_id": feedback.user_id,
                        "metadata": feedback.metadata,
                    }, f)
            except Exception:
                # Log error but don't fail collection
                pass
        
        return True

    def get_feedback(
        self,
        feedback_id: str | None = None,
        trace_id: str | None = None,
        feedback_type: FeedbackType | None = None,
    ) -> list[Feedback]:
        """
        Get feedback.

        Args:
            feedback_id: Specific feedback ID
            trace_id: Filter by trace ID
            feedback_type: Filter by type

        Returns:
            List of feedback instances
        """
        results = self._feedback

        if feedback_id:
            results = [f for f in results if f.id == feedback_id]

        if trace_id:
            results = [f for f in results if f.trace_id == trace_id]

        if feedback_type:
            results = [f for f in results if f.type == feedback_type]

        return results

    def get_statistics(self) -> dict[str, Any]:
        """
        Get feedback statistics.

        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(self._feedback),
            "by_type": {},
            "by_hour": {},
        }

        for feedback in self._feedback:
            # Count by type
            type_name = feedback.type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

            # Count by hour
            hour = int(feedback.timestamp // 3600)
            stats["by_hour"][str(hour)] = stats["by_hour"].get(str(hour), 0) + 1

        return stats

    def export(
        self,
        format: str = "json",
    ) -> str:
        """
        Export feedback.

        Args:
            format: Export format ("json" or "csv")

        Returns:
            Exported data
        """
        data = [
            {
                "id": f.id,
                "type": f.type.value,
                "message": f.message,
                "trace_id": f.trace_id,
                "user_id": f.user_id,
                "timestamp": f.timestamp,
                "metadata": f.metadata,
            }
            for f in self._feedback
        ]

        if format == "json":
            import json
            return json.dumps(data, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()

        return str(data)

    def clear(self):
        """Clear all feedback."""
        self._feedback = []


# Global feedback collector instance
_feedback_collector = FeedbackCollector()


def collect_feedback(
    feedback_type: FeedbackType,
    message: str,
    trace_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Feedback:
    """Collect feedback (convenience function)."""
    return _feedback_collector.collect(
        feedback_type, message, trace_id, user_id, metadata
    )


def get_feedback(
    feedback_id: str | None = None,
    trace_id: str | None = None,
    feedback_type: FeedbackType | None = None,
) -> list[Feedback]:
    """Get feedback (convenience function)."""
    return _feedback_collector.get_feedback(feedback_id, trace_id, feedback_type)


def get_feedback_statistics() -> dict[str, Any]:
    """Get feedback statistics (convenience function)."""
    return _feedback_collector.get_statistics()


def export_feedback(format: str = "json") -> str:
    """Export feedback (convenience function)."""
    return _feedback_collector.export(format)
