"""
客服状态同步服务测试

测试:
- 状态变更和同步
- 并发会话控制
- 状态历史记录
- 绩效统计
"""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.agent_status_service import (
    AgentInfo,
    AgentPerformance,
    AgentRole,
    AgentStatus,
    AgentStatusChange,
    AgentStatusService,
)
from utils import utcnow


class TestAgentStatus:
    """客服状态测试"""

    def test_status_values(self):
        """测试状态枚举值"""
        assert AgentStatus.ONLINE.value == "online"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.AWAY.value == "away"
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.BREAK.value == "break"


class TestAgentRole:
    """客服角色测试"""

    def test_role_values(self):
        """测试角色枚举值"""
        assert AgentRole.GENERAL.value == "general"
        assert AgentRole.TECH.value == "technical"
        assert AgentRole.VIP.value == "vip"
        assert AgentRole.SUPERVISOR.value == "supervisor"


class TestAgentInfo:
    """客服信息测试"""

    def test_agent_info_creation(self):
        """测试客服信息创建"""
        agent = AgentInfo(
            agent_id="agent_001",
            name="张客服",
            role=AgentRole.GENERAL,
            status=AgentStatus.ONLINE,
            concurrent_chats=2,
        )

        assert agent.agent_id == "agent_001"
        assert agent.name == "张客服"
        assert agent.role == AgentRole.GENERAL
        assert agent.status == AgentStatus.ONLINE
        assert agent.concurrent_chats == 2


class TestAgentStatusChange:
    """客服状态变更测试"""

    def test_status_change_creation(self):
        """测试状态变更记录创建"""
        change = AgentStatusChange(
            agent_id="agent_001",
            old_status=AgentStatus.OFFLINE,
            new_status=AgentStatus.ONLINE,
            reason="login",
        )

        assert change.agent_id == "agent_001"
        assert change.old_status == AgentStatus.OFFLINE
        assert change.new_status == AgentStatus.ONLINE
        assert change.reason == "login"
        assert change.timestamp is not None


class TestAgentStatusService:
    """客服状态服务测试"""

    def test_initial_state(self):
        """测试初始状态"""
        service = AgentStatusService()

        assert service._ws_sync is None
        assert service.MAX_HISTORY_DAYS == 30
        assert service.MAX_HISTORY_RECORDS == 1000

    def test_is_valid_status_transition(self):
        """测试状态转换合法性"""
        service = AgentStatusService()

        # 合法转换
        assert service._is_valid_status_transition("offline", "online")
        assert service._is_valid_status_transition("online", "busy")
        assert service._is_valid_status_transition("busy", "online")
        assert service._is_valid_status_transition("online", "away")

        # 非法转换
        assert not service._is_valid_status_transition("offline", "busy")
        assert not service._is_valid_status_transition("away", "busy")


class TestAgentPerformance:
    """客服绩效测试"""

    def test_performance_creation(self):
        """测试绩效创建"""
        perf = AgentPerformance(
            agent_id="agent_001",
            period_start=utcnow() - timedelta(days=7),
            period_end=utcnow(),
            total_sessions=50,
            resolved_sessions=45,
        )

        assert perf.agent_id == "agent_001"
        assert perf.total_sessions == 50
        assert perf.resolved_sessions == 45


# ==================== 集成测试 ====================
class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_status_workflow(self):
        """测试完整状态流程"""
        service = AgentStatusService()

        # 模拟 Redis 客户端
        mock_redis = MagicMock()
        mock_redis.hset = AsyncMock()
        mock_redis.expire = AsyncMock()
        mock_redis.lpush = AsyncMock()
        mock_redis.ltrim = AsyncMock()
        mock_redis.hgetall = AsyncMock(
            return_value={
                "status": "offline",
                "concurrent_chats": "0",
            }
        )

        with patch.object(service, "_fallback_manager") as mock_fallback:
            mock_fallback.execute_with_fallback = AsyncMock(
                return_value={"status": "offline", "concurrent_chats": 0}
            )

            # 获取当前状态
            status = await service.get_agent_status("agent_001")
            assert status["status"] in ["offline", "online"]
