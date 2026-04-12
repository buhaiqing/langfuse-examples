import { Badge } from '@/components/ui/badge';
import type { Agent } from '@/types/agent-workstation';

interface AgentStatusProps {
  agent: {
    name: string;
    status: Agent['status'];
    activeConversations: number;
    maxConversations: number;
  };
}

const statusConfig: Record<Agent['status'], { label: string; color: string; dot: string }> = {
  online: { label: '在线', color: 'text-green-600', dot: 'bg-green-500' },
  away: { label: '离开', color: 'text-amber-600', dot: 'bg-amber-500' },
  busy: { label: '忙碌', color: 'text-red-600', dot: 'bg-red-500' },
  offline: { label: '离线', color: 'text-gray-400', dot: 'bg-gray-400' },
};

export function AgentStatus({ agent }: AgentStatusProps) {
  const status = statusConfig[agent.status];
  const loadPercent = Math.round((agent.activeConversations / agent.maxConversations) * 100);
  const loadColor = loadPercent >= 80 ? 'text-red-600' : loadPercent >= 50 ? 'text-amber-600' : 'text-green-600';

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-200 bg-white">
      <div className="flex items-center gap-2">
        <div className="relative">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
            {agent.name.charAt(0)}
          </div>
          <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${status.dot}`} />
        </div>
        <div>
          <div className="font-medium text-gray-900 text-sm">{agent.name}</div>
          <div className={`text-xs ${status.color}`}>{status.label}</div>
        </div>
      </div>
      <div className="ml-auto flex items-center gap-4">
        <div className="text-right">
          <div className="text-xs text-gray-500">当前负载</div>
          <div className={`text-sm font-medium ${loadColor}`}>
            {agent.activeConversations}/{agent.maxConversations}
          </div>
        </div>
        <Badge
          variant={loadPercent >= 80 ? 'destructive' : 'secondary'}
          className={`text-xs ${loadPercent >= 50 && loadPercent < 80 ? 'bg-amber-100 text-amber-800' : ''}`}
        >
          {loadPercent}%
        </Badge>
      </div>
    </div>
  );
}

const mockAgent: AgentStatusProps['agent'] = {
  name: '客服小王',
  status: 'online',
  activeConversations: 3,
  maxConversations: 5,
};

export function AgentStatusBar() {
  return <AgentStatus agent={mockAgent} />;
}
