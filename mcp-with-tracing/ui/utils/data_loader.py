"""
数据加载器 - 统一的数据访问层

从项目模块加载数据，提供缓存和错误处理。
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def load_health_status() -> dict[str, Any]:
    """
    加载系统健康状态。

    Returns:
        健康状态字典，失败时返回降级数据。
    """
    try:
        # 确保 Langfuse 客户端已初始化
        from src.observability.instrumentation import get_langfuse_client, init_observability
        
        client = get_langfuse_client()
        if client is None:
            # 尝试初始化
            try:
                from src.observability.config import ObservabilityConfig
                config = ObservabilityConfig()
                init_observability(config)
            except Exception as init_error:
                logger.warning(f"Langfuse 初始化失败: {init_error}")
        
        from src.observability.health import get_health_status
        return get_health_status()
    except Exception as e:
        logger.error(f"Failed to load health status: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().timestamp(),
            "uptime_seconds": 0,
            "components": {},
            "error": str(e),
        }


def load_metrics_data(
    metric_name: str,
    hours: int = 24,
    interval_minutes: int | None = None,
) -> Any:
    """
    加载指标历史数据。

    Args:
        metric_name: 指标名称（success_rate, latency_p95, request_rate, satisfaction）
        hours: 历史数据小时数
        interval_minutes: 聚合间隔

    Returns:
        DataFrame 或 None（失败时）
    """
    try:
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(window_minutes=10)
        return collector.get_historical_data(
            metric_name=metric_name,
            hours=hours,
            interval_minutes=interval_minutes,
        )
    except Exception as e:
        logger.error(f"Failed to load metrics data for {metric_name}: {e}")
        return None


def load_current_metrics() -> dict[str, Any]:
    """
    加载当前指标值。

    Returns:
        当前指标值字典
    """
    try:
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector(window_minutes=10)

        return {
            "success_rate": collector.collect_success_rate(),
            "latency_p95": collector.collect_latency_p95(),
            "latency_p50": collector.collect_latency_p50(),
            "latency_p99": collector.collect_latency_p99(),
            "request_rate": collector.collect_request_rate(),
            "satisfaction": collector.collect_avg_satisfaction(),
            "active_sessions": collector.count_active_sessions(),
            "error_breakdown": collector.collect_error_breakdown(),
            "error_count": sum(collector.collect_error_breakdown().values()),
        }
    except Exception as e:
        logger.error(f"Failed to load current metrics: {e}")
        return {
            "success_rate": 0.0,
            "latency_p95": 0.0,
            "latency_p50": 0.0,
            "latency_p99": 0.0,
            "request_rate": 0.0,
            "satisfaction": None,
            "active_sessions": 0,
            "error_breakdown": {},
            "error_count": 0,
        }


def load_alert_rules() -> list[dict[str, Any]]:
    """
    加载告警规则列表。

    Returns:
        告警规则字典列表
    """
    try:
        from src.observability.alerting import get_alert_manager

        manager = get_alert_manager()
        rules = []

        for rule_name in manager.list_rules():
            rule = manager.get_rule(rule_name)
            if rule:
                rules.append(
                    {
                        "name": rule.name,
                        "metric": rule.metric,
                        "threshold": rule.threshold,
                        "operator": rule.operator,
                        "severity": rule.severity.value,
                        "window_minutes": rule.window_minutes,
                        "enabled": rule.enabled,
                        "channels": [c.value for c in rule.channels],
                    }
                )

        return rules
    except Exception as e:
        logger.error(f"Failed to load alert rules: {e}")
        return []


def load_triggered_alerts(limit: int = 50) -> list[dict[str, Any]]:
    """
    加载已触发的告警历史。

    Args:
        limit: 返回数量限制

    Returns:
        告警历史字典列表
    """
    try:
        from src.observability.alerting import get_alert_manager

        manager = get_alert_manager()
        alerts = manager.get_triggered_alerts()

        # 返回最近 limit 条
        recent_alerts = alerts[-limit:] if len(alerts) > limit else alerts

        return [
            {
                "triggered_at": alert.triggered_at,
                "rule_name": alert.rule.name,
                "metric": alert.rule.metric,
                "value": alert.value,
                "threshold": alert.rule.threshold,
                "severity": alert.rule.severity.value,
                "message": alert.message,
            }
            for alert in recent_alerts
        ]
    except Exception as e:
        logger.error(f"Failed to load triggered alerts: {e}")
        return []


def load_alert_statistics() -> dict[str, Any]:
    """
    加载告警统计数据。

    Returns:
        告警统计字典
    """
    try:
        from src.observability.alerting import get_alert_manager

        manager = get_alert_manager()
        return manager.get_alert_statistics()
    except Exception as e:
        logger.error(f"Failed to load alert statistics: {e}")
        return {"total_alerts": 0, "by_severity": {}, "by_rule": {}}


def load_ml_alert_statistics() -> dict[str, Any]:
    """
    加载 ML 智能告警统计数据。

    Returns:
        ML 告警统计字典
    """
    try:
        from src.observability.smart_alerting import SmartAlertManager

        smart_manager = SmartAlertManager()
        return smart_manager.get_ml_alert_statistics()
    except Exception as e:
        logger.error(f"Failed to load ML alert statistics: {e}")
        return {
            "total_ml_alerts": 0,
            "by_type": {},
            "by_metric": {},
            "last_detection": None,
        }


def load_feedback_statistics() -> dict[str, Any]:
    """
    加载反馈统计数据。

    Returns:
        反馈统计字典
    """
    try:
        from src.observability.feedback import get_feedback_statistics

        return get_feedback_statistics()
    except Exception as e:
        logger.error(f"Failed to load feedback statistics: {e}")
        return {
            "total_feedback": 0,
            "acceptance_rate": 100.0,
            "accepts": 0,
            "rejects": 0,
            "ratings_count": 0,
            "comments_count": 0,
        }


def load_all_feedback() -> list[dict[str, Any]]:
    """
    加载所有反馈数据。

    Returns:
        反馈字典列表
    """
    try:
        from src.observability.feedback import get_feedback_collector

        collector = get_feedback_collector()
        feedback_list = collector.get_all_feedback()

        return [
            {
                "trace_id": fb.trace_id,
                "feedback_type": fb.feedback_type.value,
                "value": fb.value,
                "comment": fb.comment,
                "user_id": fb.user_id,
                "created_at": fb.created_at,
            }
            for fb in feedback_list
        ]
    except Exception as e:
        logger.error(f"Failed to load all feedback: {e}")
        return []


def load_prompt_list() -> list[dict[str, Any]]:
    """
    加载提示词列表。

    Returns:
        提示词字典列表
    """
    try:
        from src.observability.prompt_versioning import get_prompt_version_manager

        manager = get_prompt_version_manager()
        prompts = []

        for prompt_id in manager.list_prompts():
            versions = manager.get_all_versions(prompt_id)
            active_version = manager.get_active_version(prompt_id)

            prompts.append(
                {
                    "prompt_id": prompt_id,
                    "version_count": len(versions),
                    "ab_test_enabled": manager.ab_test_enabled(prompt_id),
                    "active_version": active_version,
                }
            )

        return prompts
    except Exception as e:
        logger.error(f"Failed to load prompt list: {e}")
        return []


def load_prompt_versions(prompt_id: str) -> list[dict[str, Any]]:
    """
    加载指定提示词的所有版本。

    Args:
        prompt_id: 提示词 ID

    Returns:
        版本字典列表
    """
    try:
        from src.observability.prompt_versioning import get_prompt_version_manager

        manager = get_prompt_version_manager()
        versions = manager.get_all_versions(prompt_id)

        return [
            {
                "prompt_id": v.prompt_id,
                "version": v.version,
                "description": v.description,
                "created_at": v.created_at,
                "metadata": v.metadata,
            }
            for v in versions
        ]
    except Exception as e:
        logger.error(f"Failed to load prompt versions for {prompt_id}: {e}")
        return []


def load_cache_stats() -> dict[str, Any]:
    """
    加载缓存统计信息。

    Returns:
        缓存统计字典
    """
    try:
        from src.observability.metrics_collector import MetricsCollector

        collector = MetricsCollector()
        return collector.get_cache_stats()
    except Exception as e:
        logger.error(f"Failed to load cache stats: {e}")
        return {
            "hit_rate": 0.0,
            "size": 0,
            "max_size": 0,
            "ttl_seconds": 0,
        }
