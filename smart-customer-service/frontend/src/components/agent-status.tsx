/**
 * 客服状态管理组件
 * 
 * 功能：
 * - 在线/忙碌/离开状态切换
 * - 并发会话数显示
 * - 状态同步
 * - 自动状态切换
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Sun,
  Moon,
  Coffee,
  Users,
  Clock,
  CheckCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { wsClient } from '@/lib/websocket';

export type AgentStatus = 'online' | 'busy' | 'away' | 'offline';

interface AgentStatusManagerProps {
  agentId: string;
  onStatusChange?: (status: AgentStatus) => void;
}

const STATUS_CONFIG = {
  online: {
    label: '在线',
    icon: Sun,
    color: 'bg-green-500',
    description: '可以接收新会话',
  },
  busy: {
    label: '忙碌',
    icon: Moon,
    color: 'bg-yellow-500',
    description: '暂不接收新会话',
  },
  away: {
    label: '离开',
    icon: Coffee,
    color: 'bg-orange-500',
    description: '暂时离开',
  },
  offline: {
    label: '离线',
    icon: CheckCircle,
    color: 'bg-gray-500',
    description: '已下线',
  },
};

interface AgentStats {
  concurrentChats: number;
  maxConcurrentChats: number;
  totalChatsToday: number;
  avgResponseTime: number; // 秒
}

export function AgentStatusManager({ agentId, onStatusChange }: AgentStatusManagerProps) {
  const [status, setStatus] = useState<AgentStatus>('online');
  const [isOpen, setIsOpen] = useState(false);
  const [stats, setStats] = useState<AgentStats>({
    concurrentChats: 0,
    maxConcurrentChats: 5,
    totalChatsToday: 0,
    avgResponseTime: 0,
  });

  useEffect(() => {
    // 连接 WebSocket 接收状态更新
    wsClient.connect().catch(console.error);

    wsClient.on('status_update', handleStatusUpdate);
    wsClient.on('stats_update', handleStatsUpdate);

    // 定时同步状态
    const interval = setInterval(syncStatus, 30000); // 30 秒同步一次

    return () => {
      wsClient.disconnect();
      clearInterval(interval);
    };
  }, []);

  function handleStatusUpdate(message: any) {
    console.log('收到状态更新:', message);
    if (message.agent_id === agentId) {
      setStatus(message.status as AgentStatus);
    }
  }

  function handleStatsUpdate(message: any) {
    console.log('收到统计更新:', message);
    setStats(message.stats as AgentStats);
  }

  async function syncStatus() {
    // TODO: 调用 API 同步状态
    try {
      // const response = await fetch('/api/v1/agent/status', {
      //   headers: { 'X-API-Key': API_KEY }
      // });
      // const data = await response.json();
      // setStats(data.stats);
    } catch (error) {
      console.error('同步状态失败:', error);
    }
  }

  async function changeStatus(newStatus: AgentStatus) {
    setStatus(newStatus);
    
    // 通知服务器
    try {
      wsClient.send({
        type: 'status_change',
        session_id: `agent:${agentId}`,
        payload: { status: newStatus },
      });

      // TODO: 调用 API 更新状态
      // await fetch('/api/v1/agent/status', {
      //   method: 'PUT',
      //   headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
      //   body: JSON.stringify({ status: newStatus })
      // });

      onStatusChange?.(newStatus);
      setIsOpen(false);
    } catch (error) {
      console.error('更新状态失败:', error);
      // 恢复原状态
      setStatus(status);
    }
  }

  const CurrentIcon = STATUS_CONFIG[status].icon;
  const currentConfig = STATUS_CONFIG[status];

  const capacityPercentage = (stats.concurrentChats / stats.maxConcurrentChats) * 100;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('gap-2 relative', capacityPercentage > 80 && 'animate-pulse')}
        >
          <div className={cn('w-2 h-2 rounded-full', currentConfig.color)} />
          <CurrentIcon className="h-4 w-4" />
          <span>{currentConfig.label}</span>
          {stats.concurrentChats > 0 && (
            <Badge variant="secondary" className="text-xs">
              {stats.concurrentChats}/{stats.maxConcurrentChats}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-4" align="end">
        <div className="space-y-4">
          {/* 当前状态 */}
          <div className="flex items-center gap-3">
            <div className={cn('w-3 h-3 rounded-full', currentConfig.color)} />
            <div>
              <p className="font-semibold">{currentConfig.label}</p>
              <p className="text-xs text-muted-foreground">{currentConfig.description}</p>
            </div>
          </div>

          {/* 并发会话数 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span>当前会话</span>
              </div>
              <span className="font-medium">
                {stats.concurrentChats}/{stats.maxConcurrentChats}
              </span>
            </div>
            <Progress value={capacityPercentage} className="h-2" />
            {capacityPercentage > 80 && (
              <p className="text-xs text-yellow-600">
                        会话数接近上限，建议切换到"忙碌"状态
              </p>
            )}
          </div>

          {/* 今日统计 */}
          <div className="grid grid-cols-2 gap-3 pt-3 border-t">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">今日会话</p>
                <p className="font-medium">{stats.totalChatsToday}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">平均响应</p>
                <p className="font-medium">{stats.avgResponseTime.toFixed(1)}s</p>
              </div>
            </div>
          </div>

          {/* 状态切换按钮 */}
          <div className="grid grid-cols-2 gap-2 pt-3 border-t">
            {(Object.keys(STATUS_CONFIG) as AgentStatus[]).map((s) => {
              const Config = STATUS_CONFIG[s];
              const Icon = Config.icon;
              const isSelected = status === s;

              return (
                <Button
                  key={s}
                  variant={isSelected ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => changeStatus(s)}
                  className="justify-start gap-2"
                >
                  <Icon className="h-4 w-4" />
                  {Config.label}
                </Button>
              );
            })}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
