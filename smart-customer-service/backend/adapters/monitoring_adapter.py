"""监控系统适配器"""

from datetime import datetime, timedelta
from typing import Any

from utils.api_client import APIClient


class PrometheusClient(APIClient):
    """Prometheus API 客户端"""

    async def query(self, promql: str) -> dict[str, Any]:
        """执行 PromQL 查询"""
        return await self.get(
            "/api/v1/query",
            params={"query": promql},
        )

    async def query_range(
        self, promql: str, start: datetime, end: datetime, step: str = "5m"
    ) -> dict[str, Any]:
        """范围查询"""
        return await self.get(
            "/api/v1/query_range",
            params={
                "query": promql,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": step,
            },
        )


class MonitoringService:
    """监控服务封装"""

    def __init__(self, prometheus_url: str = ""):
        self.prometheus = PrometheusClient(prometheus_url)

    async def check_service_status(self, service_name: str) -> dict[str, Any]:
        """
        检查服务状态

        Args:
            service_name: 服务名称

        Returns:
            服务状态信息
        """
        promql = f'up{{service="{service_name}"}}'
        result = await self.prometheus.query(promql)

        status = "up" if result.get("data", {}).get("result", []) else "down"

        return {
            "service_name": service_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_recent_alerts(self, hours: int = 24) -> list[dict[str, Any]]:
        """
        获取最近告警

        Args:
            hours: 时间范围（小时）

        Returns:
            告警列表
        """
        end = datetime.now()
        start = end - timedelta(hours=hours)

        promql = 'ALERTS{alertstate="firing"}'
        result = await self.prometheus.query_range(promql, start, end)

        alerts = []
        for metric in result.get("data", {}).get("result", []):
            alerts.append(
                {
                    "alert_name": metric["metric"].get("alertname"),
                    "severity": metric["metric"].get("severity"),
                    "status": metric["values"][-1][1] if metric["values"] else "unknown",
                    "timestamp": metric["values"][-1][0] if metric["values"] else None,
                }
            )

        return alerts


monitoring_service = MonitoringService()
