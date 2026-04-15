"""
客服状态同步服务

提供:
- 客服状态实时同步（在线/离线/忙碌）
- 并发会话数管理
- 状态变更历史记录
- 客服绩效统计报表
- 状态变更广播通知
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from storage.redis_client import redis_client, RedisKeys
from storage.redis_fallback import get_redis_fallback_manager
from services.websocket_sync import (
    get_ws_sync_service,
    WSMessageType,
)

logger = logging.getLogger(__name__)


# ==================== 状态定义 ====================
class AgentStatus(str, Enum):
    """客服状态"""
    ONLINE = "online"       # 在线可用
    BUSY = "busy"           # 繁忙（并发达到上限）
    AWAY = "away"           # 暂时离开
    OFFLINE = "offline"     # 离线
    BREAK = "break"         # 休息


class AgentRole(str, Enum):
    """客服角色"""
    GENERAL = "general"     # 通用客服
    TECH = "technical"      # 技术客服
    VIP = "vip"             # VIP 专属客服
    SUPERVISOR = "supervisor"  # 主管


@dataclass
class AgentInfo:
    """客服信息"""
    agent_id: str
    name: str
    role: AgentRole = AgentRole.GENERAL
    status: AgentStatus = AgentStatus.OFFLINE
    concurrent_chats: int = 0
    max_concurrent_chats: int = 5
    skills: List[str] = field(default_factory=list)
    department: Optional[str] = None
    email: Optional[str] = None


@dataclass
class AgentStatusChange:
    """客服状态变更记录"""
    agent_id: str
    old_status: AgentStatus
    new_status: AgentStatus
    reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None  # 关联的会话ID（如果有）


@dataclass
class AgentPerformance:
    """客服绩效"""
    agent_id: str
    period_start: datetime
    period_end: datetime

    # 会话统计
    total_sessions: int = 0
    resolved_sessions: int = 0
    escalated_sessions: int = 0
    avg_resolution_time_minutes: float = 0.0

    # 消息统计
    total_messages: int = 0
    avg_response_time_seconds: float = 0.0

    # 评分统计
    avg_satisfaction_score: float = 0.0
    total_ratings: int = 0

    # 工作时间
    online_hours: float = 0.0
    busy_hours: float = 0.0


# ==================== 客服状态服务 ====================
class AgentStatusService:
    """
    客服状态服务

    管理:
    - 状态变更和同步
    - 并发会话控制
    - 历史记录
    - 绩效统计
    """

    # Redis 键
    KEY_AGENT_STATUS = "agent:{agent_id}:status"
    KEY_AGENT_INFO = "agent:{agent_id}:info"
    KEY_AGENT_HISTORY = "agent:{agent_id}:history"
    KEY_AGENT_SESSIONS = "agent:{agent_id}:sessions"
    KEY_AGENT_STATS_DAILY = "agent:{agent_id}:stats:daily:{date}"
    KEY_ALL_AGENTS = "agents:all"

    # 配置
    MAX_HISTORY_DAYS = 30
    MAX_HISTORY_RECORDS = 1000

    def __init__(self):
        self._ws_sync = None
        self._fallback_manager = get_redis_fallback_manager()

    async def initialize(self):
        """初始化服务"""
        self._ws_sync = get_ws_sync_service()
        await self._ws_sync.initialize()

    async def set_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        concurrent_chats: Optional[int] = None,
        reason: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """
        设置客服状态

        Args:
            agent_id: 客服ID
            status: 新状态
            concurrent_chats: 当前并发会话数（可选）
            reason: 变更原因
            session_id: 关联会话ID

        Returns:
            是否成功
        """
        # 1. 获取当前状态
        current_status = await self.get_agent_status(agent_id)
        old_status = current_status.get("status", AgentStatus.OFFLINE.value)

        # 2. 检查状态转换是否合法
        if not self._is_valid_status_transition(old_status, status.value):
            logger.warning(
                f"客服 {agent_id} 状态转换不合法: {old_status} -> {status.value}"
            )
            return False

        # 3. 更新 Redis
        status_data = {
            "status": status.value,
            "concurrent_chats": concurrent_chats or current_status.get("concurrent_chats", 0),
            "updated_at": datetime.utcnow().isoformat(),
        }

        await self._fallback_manager.execute_with_fallback(
            operation=lambda: self._update_status_in_redis(agent_id, status_data),
            key=f"agent_status:{agent_id}",
            fallback_value=True,
        )

        # 4. 记录历史
        await self._record_status_change(
            agent_id, old_status, status.value, reason, session_id
        )

        # 5. 广播状态变更
        if self._ws_sync:
            await self._ws_sync.broadcast_agent_status(
                agent_id=agent_id,
                status=status.value,
                concurrent_chats=status_data["concurrent_chats"],
            )

        logger.info(
            f"客服 {agent_id} 状态变更: {old_status} -> {status.value} "
            f"(并发: {status_data['concurrent_chats']})"
        )

        return True

    async def _update_status_in_redis(self, agent_id: str, status_data: Dict[str, Any]):
        """更新 Redis 中的客服状态"""
        key = self.KEY_AGENT_STATUS.format(agent_id=agent_id)

        await redis_client._client.hset(
            key,
            mapping={
                "status": status_data["status"],
                "concurrent_chats": str(status_data["concurrent_chats"]),
                "updated_at": status_data["updated_at"],
            },
        )

        # 设置过期时间
        await redis_client._client.expire(key, 3600 * 24)  # 24小时

        # 更新全局客服列表
        if status_data["status"] == AgentStatus.ONLINE.value:
            await redis_client._client.sadd(self.KEY_ALL_AGENTS, agent_id)
        elif status_data["status"] == AgentStatus.OFFLINE.value:
            await redis_client._client.srem(self.KEY_ALL_AGENTS, agent_id)

    async def _record_status_change(
        self,
        agent_id: str,
        old_status: str,
        new_status: str,
        reason: Optional[str],
        session_id: Optional[str],
    ):
        """记录状态变更历史"""
        history_key = self.KEY_AGENT_HISTORY.format(agent_id=agent_id)

        change_record = AgentStatusChange(
            agent_id=agent_id,
            old_status=AgentStatus(old_status),
            new_status=AgentStatus(new_status),
            reason=reason,
            session_id=session_id,
        )

        # 添加到列表
        await redis_client._client.lpush(
            history_key,
            json.dumps({
                "agent_id": change_record.agent_id,
                "old_status": change_record.old_status.value,
                "new_status": change_record.new_status.value,
                "reason": change_record.reason,
                "session_id": change_record.session_id,
                "timestamp": change_record.timestamp,
            }),
        )

        # 限制历史记录数量
        await redis_client._client.ltrim(history_key, 0, self.MAX_HISTORY_RECORDS - 1)

        # 设置过期时间
        await redis_client._client.expire(history_key, self.MAX_HISTORY_DAYS * 24 * 3600)

    def _is_valid_status_transition(self, old_status: str, new_status: str) -> bool:
        """检查状态转换是否合法"""
        # 合法转换矩阵
        valid_transitions = {
            AgentStatus.OFFLINE.value: [AgentStatus.ONLINE.value, AgentStatus.BREAK.value],
            AgentStatus.ONLINE.value: [AgentStatus.BUSY.value, AgentStatus.AWAY.value,
                                        AgentStatus.OFFLINE.value, AgentStatus.BREAK.value],
            AgentStatus.BUSY.value: [AgentStatus.ONLINE.value, AgentStatus.AWAY.value,
                                       AgentStatus.OFFLINE.value, AgentStatus.BREAK.value],
            AgentStatus.AWAY.value: [AgentStatus.ONLINE.value, AgentStatus.OFFLINE.value],
            AgentStatus.BREAK.value: [AgentStatus.ONLINE.value, AgentStatus.OFFLINE.value],
        }

        return new_status in valid_transitions.get(old_status, [])

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """获取客服状态"""
        key = self.KEY_AGENT_STATUS.format(agent_id=agent_id)

        result = await self._fallback_manager.execute_with_fallback(
            operation=lambda: redis_client._client.hgetall(key),
            key=f"agent_status:{agent_id}",
            fallback_value={"status": AgentStatus.OFFLINE.value, "concurrent_chats": 0},
        )

        if result and isinstance(result, dict):
            # 转换字节类型
            status = {}
            for k, v in result.items():
                if isinstance(k, bytes):
                    k = k.decode("utf-8")
                if isinstance(v, bytes):
                    v = v.decode("utf-8")
                status[k] = v

            return {
                "status": status.get("status", AgentStatus.OFFLINE.value),
                "concurrent_chats": int(status.get("concurrent_chats", 0)),
                "updated_at": status.get("updated_at", ""),
            }

        return {"status": AgentStatus.OFFLINE.value, "concurrent_chats": 0}

    async def get_all_online_agents(self) -> List[Dict[str, Any]]:
        """获取所有在线客服"""
        agent_ids = await redis_client._client.smembers(self.KEY_ALL_AGENTS)

        online_agents = []
        for agent_id in agent_ids:
            if isinstance(agent_id, bytes):
                agent_id = agent_id.decode("utf-8")

            status = await self.get_agent_status(agent_id)
            if status.get("status") == AgentStatus.ONLINE.value:
                online_agents.append({
                    "agent_id": agent_id,
                    "status": status.get("status"),
                    "concurrent_chats": status.get("concurrent_chats", 0),
                    "updated_at": status.get("updated_at"),
                })

        return online_agents

    async def get_available_agents(
        self,
        min_capacity: int = 1,
        skills: Optional[List[str]] = None,
    ) -> List[str]:
        """
        获取可用客服列表

        Args:
            min_capacity: 最小可用容量（max_concurrent - current）
            skills: 需要的技能列表

        Returns:
            可用客服ID列表
        """
        online_agents = await self.get_all_online_agents()

        available = []
        for agent in online_agents:
            # 检查容量
            current = agent.get("concurrent_chats", 0)
            max_capacity = 5  # TODO: 从客服信息获取

            if max_capacity - current < min_capacity:
                continue

            # TODO: 检查技能匹配

            available.append(agent["agent_id"])

        return available

    async def assign_session_to_agent(
        self,
        session_id: str,
        agent_id: str,
    ) -> bool:
        """
        分配会话给客服

        Args:
            session_id: 会话ID
            agent_id: 客服ID

        Returns:
            是否成功
        """
        # 1. 检查客服是否可用
        status = await self.get_agent_status(agent_id)
        if status.get("status") != AgentStatus.ONLINE.value:
            logger.warning(f"客服 {agent_id} 不在线，无法分配会话")
            return False

        current_chats = status.get("concurrent_chats", 0)
        max_chats = 5  # TODO: 从客服信息获取

        if current_chats >= max_chats:
            logger.warning(f"客服 {agent_id} 已达到最大并发数 {max_chats}")
            return False

        # 2. 更新并发数
        new_concurrent = current_chats + 1
        new_status = (
            AgentStatus.BUSY.value if new_concurrent >= max_chats
            else AgentStatus.ONLINE.value
        )

        await self.set_agent_status(
            agent_id=agent_id,
            status=AgentStatus(new_status),
            concurrent_chats=new_concurrent,
            reason="session_assigned",
            session_id=session_id,
        )

        # 3. 记录会话分配
        sessions_key = self.KEY_AGENT_SESSIONS.format(agent_id=agent_id)
        await redis_client._client.sadd(sessions_key, session_id)

        logger.info(f"会话 {session_id} 分配给客服 {agent_id}")

        return True

    async def release_session_from_agent(
        self,
        session_id: str,
        agent_id: str,
    ) -> bool:
        """
        从客服释放会话

        Args:
            session_id: 会话ID
            agent_id: 客服ID

        Returns:
            是否成功
        """
        # 1. 从会话列表移除
        sessions_key = self.KEY_AGENT_SESSIONS.format(agent_id=agent_id)
        await redis_client._client.srem(sessions_key, session_id)

        # 2. 更新并发数
        status = await self.get_agent_status(agent_id)
        current_chats = status.get("concurrent_chats", 0)

        new_concurrent = max(0, current_chats - 1)

        await self.set_agent_status(
            agent_id=agent_id,
            status=AgentStatus.ONLINE,
            concurrent_chats=new_concurrent,
            reason="session_released",
            session_id=session_id,
        )

        logger.info(f"客服 {agent_id} 释放会话 {session_id}")

        return True

    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取客服状态变更历史"""
        history_key = self.KEY_AGENT_HISTORY.format(agent_id=agent_id)

        records = await redis_client._client.lrange(history_key, 0, limit - 1)

        history = []
        for record in records:
            if isinstance(record, bytes):
                record = record.decode("utf-8")
            history.append(json.loads(record))

        return history

    async def record_performance(
        self,
        agent_id: str,
        metrics: Dict[str, Any],
    ):
        """记录客服绩效指标"""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        stats_key = self.KEY_AGENT_STATS_DAILY.format(
            agent_id=agent_id, date=date_str
        )

        # 增加各项指标
        for metric_name, value in metrics.items():
            await redis_client._client.hincrbyfloat(stats_key, metric_name, value)

        # 设置过期时间（90天）
        await redis_client._client.expire(stats_key, 90 * 24 * 3600)

    async def get_agent_performance(
        self,
        agent_id: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """获取客服绩效统计"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        performance = AgentPerformance(
            agent_id=agent_id,
            period_start=start_date,
            period_end=end_date,
        )

        # 汇总每日数据
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            stats_key = self.KEY_AGENT_STATS_DAILY.format(
                agent_id=agent_id, date=date_str
            )

            daily_stats = await redis_client._client.hgetall(stats_key)

            if daily_stats:
                performance.total_sessions += int(daily_stats.get("total_sessions", 0) or 0)
                performance.resolved_sessions += int(daily_stats.get("resolved_sessions", 0) or 0)
                performance.escalated_sessions += int(daily_stats.get("escalated_sessions", 0) or 0)
                performance.total_messages += int(daily_stats.get("total_messages", 0) or 0)
                performance.total_ratings += int(daily_stats.get("total_ratings", 0) or 0)

            current_date += timedelta(days=1)

        # 计算平均值
        if performance.total_ratings > 0:
            # TODO: 从历史数据计算平均满意度
            performance.avg_satisfaction_score = 4.5  # 示例值

        return {
            "agent_id": performance.agent_id,
            "period": {
                "start": performance.period_start.isoformat(),
                "end": performance.period_end.isoformat(),
                "days": days,
            },
            "sessions": {
                "total": performance.total_sessions,
                "resolved": performance.resolved_sessions,
                "escalated": performance.escalated_sessions,
                "resolution_rate": (
                    performance.resolved_sessions / performance.total_sessions * 100
                    if performance.total_sessions > 0 else 0
                ),
            },
            "messages": {
                "total": performance.total_messages,
            },
            "ratings": {
                "total": performance.total_ratings,
                "avg_satisfaction": performance.avg_satisfaction_score,
            },
        }

    async def get_all_agents_performance(
        self,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """获取所有客服绩效"""
        agent_ids = await redis_client._client.smembers(self.KEY_ALL_AGENTS)

        performances = []
        for agent_id in agent_ids:
            if isinstance(agent_id, bytes):
                agent_id = agent_id.decode("utf-8")

            perf = await self.get_agent_performance(agent_id, days)
            performances.append(perf)

        return performances


# ==================== 全局实例 ====================
_agent_status_service: Optional[AgentStatusService] = None


def get_agent_status_service() -> AgentStatusService:
    """获取客服状态服务"""
    global _agent_status_service

    if _agent_status_service is None:
        _agent_status_service = AgentStatusService()

    return _agent_status_service


async def init_agent_status_service() -> AgentStatusService:
    """初始化客服状态服务"""
    global _agent_status_service

    _agent_status_service = AgentStatusService()
    await _agent_status_service.initialize()

    return _agent_status_service


# ==================== 导出 ====================
__all__ = [
    "AgentStatus",
    "AgentRole",
    "AgentInfo",
    "AgentStatusChange",
    "AgentPerformance",
    "AgentStatusService",
    "get_agent_status_service",
    "init_agent_status_service",
]