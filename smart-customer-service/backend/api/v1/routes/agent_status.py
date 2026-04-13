"""
客服状态管理 API

提供客服状态管理、查询和同步功能
"""

import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from storage.redis_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["客服管理"])


class AgentStatusUpdate(BaseModel):
    """客服状态更新请求"""

    status: str = Field(..., description="状态：online/busy/away/offline")
    concurrent_chats: int = Field(default=0, description="并发会话数")


class AgentStatusResponse(BaseModel):
    """客服状态响应"""

    agent_id: str
    status: str
    concurrent_chats: int
    updated_at: str


class OnlineAgentsResponse(BaseModel):
    """在线客服列表响应"""

    agents: List[AgentStatusResponse]
    total: int
    online_count: int


@router.put("/status/{agent_id}", response_model=AgentStatusResponse)
async def update_agent_status(
    agent_id: str,
    status_update: AgentStatusUpdate,
):
    """更新客服状态"""
    try:
        await redis_client.set_agent_status(
            agent_id=agent_id,
            status=status_update.status,
            concurrent_chats=status_update.concurrent_chats,
        )

        return AgentStatusResponse(
            agent_id=agent_id,
            status=status_update.status,
            concurrent_chats=status_update.concurrent_chats,
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"更新客服状态失败：{e}")
        raise HTTPException(status_code=500, detail=f"更新客服状态失败：{str(e)}")


@router.get("/status/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(agent_id: str):
    """获取客服状态"""
    try:
        status = await redis_client.get_agent_status(agent_id)

        if not status:
            raise HTTPException(status_code=404, detail="客服状态不存在")

        return AgentStatusResponse(
            agent_id=agent_id,
            status=status.get("status", "offline"),
            concurrent_chats=status.get("concurrent_chats", 0),
            updated_at=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取客服状态失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取客服状态失败：{str(e)}")


@router.get("/online", response_model=OnlineAgentsResponse)
async def get_online_agents():
    """
    获取所有在线客服 - 优化版本
    
    使用 Redis Pipeline 批量查询，避免 N+1 问题
    """
    try:
        # 获取所有 WebSocket 连接的客服
        agent_ids = await redis_client.get_websocket_agents()
        
        if not agent_ids:
            return OnlineAgentsResponse(agents=[], total=0, online_count=0)

        # 使用 Pipeline 批量查询所有客服状态（解决 N+1 问题）
        status_results = await redis_client.get_multiple_agent_status(list(agent_ids))
        
        online_agents = []
        for agent_id, status in status_results.items():
            if status and status.get("status") == "online":
                online_agents.append(
                    AgentStatusResponse(
                        agent_id=agent_id,
                        status="online",
                        concurrent_chats=status.get("concurrent_chats", 0),
                        updated_at=datetime.utcnow().isoformat(),
                    )
                )

        return OnlineAgentsResponse(
            agents=online_agents,
            total=len(agent_ids),
            online_count=len(online_agents)
        )
    except Exception as e:
        logger.error(f"获取在线客服失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取在线客服失败：{str(e)}")


@router.get("/stats")
async def get_agent_statistics():
    """
    获取客服统计信息
    
    包括：总客服数、在线数、忙碌数、平均并发会话数
    """
    try:
        agent_ids = await redis_client.get_websocket_agents()
        
        if not agent_ids:
            return {
                "total_agents": 0,
                "online_count": 0,
                "busy_count": 0,
                "away_count": 0,
                "offline_count": 0,
                "avg_concurrent_chats": 0,
            }

        # 批量获取所有客服状态
        status_results = await redis_client.get_multiple_agent_status(list(agent_ids))
        
        # 统计各状态数量
        status_counts = {"online": 0, "busy": 0, "away": 0, "offline": 0}
        total_concurrent = 0
        
        for status in status_results.values():
            if status:
                agent_status = status.get("status", "offline")
                status_counts[agent_status] = status_counts.get(agent_status, 0) + 1
                total_concurrent += status.get("concurrent_chats", 0)
        
        avg_concurrent = total_concurrent / len(agent_ids) if agent_ids else 0

        return {
            "total_agents": len(agent_ids),
            "online_count": status_counts.get("online", 0),
            "busy_count": status_counts.get("busy", 0),
            "away_count": status_counts.get("away", 0),
            "offline_count": status_counts.get("offline", 0),
            "avg_concurrent_chats": round(avg_concurrent, 2),
            "total_concurrent_chats": total_concurrent,
        }
    except Exception as e:
        logger.error(f"获取客服统计失败：{e}")
        raise HTTPException(status_code=500, detail=f"获取客服统计失败：{str(e)}")
