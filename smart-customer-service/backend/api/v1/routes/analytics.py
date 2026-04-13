"""
数据分析 API 路由

提供:
- 概览统计
- 意图分布
- 客服绩效
- 实时指标
- 趋势分析
- 报表导出
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["数据分析"])


class OverviewResponse(BaseModel):
    """概览统计响应"""

    period: dict
    sessions: dict
    performance: dict
    satisfaction: dict


class IntentDistributionResponse(BaseModel):
    """意图分布响应"""

    period: dict
    total_intents: int
    distribution: list
    accuracy: dict


class AgentPerformanceResponse(BaseModel):
    """客服绩效响应"""

    agent_id: Optional[str]
    period: dict
    metrics: Optional[dict]
    agents: Optional[list]
    summary: Optional[dict]


class RealtimeMetricsResponse(BaseModel):
    """实时指标响应"""

    timestamp: str
    sessions: dict
    performance: dict
    escalations: dict
    system: dict


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(days: int = Query(default=7, ge=1, le=90, description="统计天数")):
    """获取概览统计"""
    return await analytics_service.get_overview(days)


@router.get("/intent-distribution", response_model=IntentDistributionResponse)
async def get_intent_distribution(
    days: int = Query(default=7, ge=1, le=90, description="统计天数"),
):
    """获取意图分布统计"""
    return await analytics_service.get_intent_distribution(days)


@router.get("/agent-performance", response_model=AgentPerformanceResponse)
async def get_agent_performance(
    agent_id: Optional[str] = Query(default=None, description="客服 ID"),
    days: int = Query(default=7, ge=1, le=90, description="统计天数"),
):
    """获取客服绩效统计"""
    return await analytics_service.get_agent_performance(agent_id, days)


@router.get("/realtime", response_model=RealtimeMetricsResponse)
async def get_realtime_metrics():
    """获取实时监控指标"""
    return await analytics_service.get_realtime_metrics()


@router.get("/trend/{metric}")
async def get_trend_analysis(
    metric: Literal["sessions", "resolution_rate", "satisfaction", "escalations"],
    days: int = Query(default=30, ge=1, le=365, description="统计天数"),
):
    """获取趋势分析"""
    return await analytics_service.get_trend_analysis(metric, days)


@router.get("/export/{report_type}")
async def export_report(
    report_type: Literal["overview", "performance", "satisfaction"],
    format: Literal["json", "csv"] = Query(default="json", description="导出格式"),
):
    """导出报表"""
    return await analytics_service.export_report(report_type, format)


@router.get("/dashboard")
async def get_dashboard_data():
    """获取仪表板数据（聚合所有关键指标）"""
    overview = await analytics_service.get_overview(7)
    realtime = await analytics_service.get_realtime_metrics()
    intents = await analytics_service.get_intent_distribution(7)

    return {
        "overview": overview,
        "realtime": realtime,
        "intent_distribution": intents,
        "generated_at": "2026-04-13T10:00:00Z",
    }
