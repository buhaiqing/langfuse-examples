"""
Token Tracker for LLM usage monitoring.

Provides accurate token counting for multiple LLM providers
with real-time tracking and analytics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    COHERE = "cohere"
    BEDROCK = "bedrock"


@dataclass
class TokenUsage:
    """Token usage record for a single request."""

    provider: LLMProvider
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenStats:
    """Aggregated token statistics."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0

    def add_usage(self, usage: TokenUsage):
        """Add token usage to stats."""
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.total_cost += usage.cost
        self.request_count += 1


TOKEN_PRICES: dict[LLMProvider, dict[str, dict[str, float]]] = {
    LLMProvider.OPENAI: {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
    },
    LLMProvider.ANTHROPIC: {
        "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
        "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
        "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
    },
    LLMProvider.AZURE: {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-35-turbo": {"prompt": 0.0015, "completion": 0.002},
    },
    LLMProvider.COHERE: {
        "command": {"prompt": 0.001, "completion": 0.002},
        "command-light": {"prompt": 0.0003, "completion": 0.0006},
    },
    LLMProvider.BEDROCK: {
        "anthropic.claude-v2": {"prompt": 0.008, "completion": 0.024},
        "ai21.j2-mid-v1": {"prompt": 0.0125, "completion": 0.0125},
    },
}


class TokenTracker:
    """
    Real-time token tracker for LLM usage monitoring.

    Tracks token usage across multiple providers and models with
    automatic cost calculation.

    Example:
        tracker = TokenTracker()
        tracker.record_usage(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
        )
        stats = tracker.get_stats()
    """

    def __init__(self):
        """Initialize the token tracker."""
        self._usages: list[TokenUsage] = []
        self._global_stats = TokenStats()
        self._model_stats: dict[str, TokenStats] = {}

    def record_usage(
        self,
        provider: LLMProvider,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        metadata: dict[str, Any] | None = None,
    ) -> TokenUsage:
        """
        Record token usage for a request.

        Args:
            provider: LLM provider
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            metadata: Optional metadata

        Returns:
            TokenUsage record
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(provider, model, prompt_tokens, completion_tokens)

        usage = TokenUsage(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            metadata=metadata or {},
        )

        self._usages.append(usage)
        self._global_stats.add_usage(usage)

        model_key = f"{provider.value}:{model}"
        if model_key not in self._model_stats:
            self._model_stats[model_key] = TokenStats()
        self._model_stats[model_key].add_usage(usage)

        return usage

    def _calculate_cost(
        self, provider: LLMProvider, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """
        Calculate cost for token usage.

        Args:
            provider: LLM provider
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in USD
        """
        if provider not in TOKEN_PRICES:
            return 0.0

        model_pricing = TOKEN_PRICES[provider].get(model)
        if not model_pricing:
            return 0.0

        prompt_cost = (prompt_tokens / 1000) * model_pricing.get("prompt", 0)
        completion_cost = (completion_tokens / 1000) * model_pricing.get("completion", 0)

        return prompt_cost + completion_cost

    def get_stats(self) -> TokenStats:
        """
        Get aggregated token statistics.

        Returns:
            Global token statistics
        """
        return self._global_stats

    def get_model_stats(self) -> dict[str, TokenStats]:
        """
        Get per-model token statistics.

        Returns:
            Dictionary of model key to stats
        """
        return self._model_stats

    def get_top_models(self, limit: int = 5) -> list[tuple[str, TokenStats]]:
        """
        Get top N models by token usage.

        Args:
            limit: Number of top models to return

        Returns:
            List of (model_key, stats) tuples sorted by tokens
        """
        sorted_models = sorted(
            self._model_stats.items(), key=lambda x: x[1].total_tokens, reverse=True
        )
        return sorted_models[:limit]

    def reset(self):
        """Reset all tracking data."""
        self._usages.clear()
        self._global_stats = TokenStats()
        self._model_stats.clear()

    def estimate_quota_usage(
        self, daily_quota: int, current_usage: int | None = None
    ) -> dict[str, Any]:
        """
        Estimate quota usage percentage.

        Args:
            daily_quota: Daily token quota
            current_usage: Current usage (uses global stats if None)

        Returns:
            Dictionary with usage percentage and projections
        """
        if current_usage is None:
            current_usage = self._global_stats.total_tokens

        percentage = (current_usage / daily_quota) * 100 if daily_quota > 0 else 0
        remaining = max(0, daily_quota - current_usage)

        return {
            "quota": daily_quota,
            "used": current_usage,
            "percentage": percentage,
            "remaining": remaining,
            "exceeded": current_usage > daily_quota,
        }
