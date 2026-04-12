import { useConversationList } from '@/hooks/use-agent-workstation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import type { ConversationListItem, Priority, ConversationStatus } from '@/types/agent-workstation';

const priorityConfig: Record<Priority, { label: string; variant: 'destructive' | 'secondary' | 'outline' }> = {
  urgent: { label: '紧急', variant: 'destructive' },
  high: { label: '高', variant: 'secondary' },
  medium: { label: '中', variant: 'secondary' },
  low: { label: '低', variant: 'outline' },
};

const statusConfig: Record<ConversationStatus, { label: string; color: string }> = {
  pending: { label: '待处理', color: 'text-amber-600' },
  active: { label: '进行中', color: 'text-green-600' },
  resolved: { label: '已解决', color: 'text-gray-500' },
  closed: { label: '已关闭', color: 'text-gray-400' },
};

const reasonLabels: Record<string, string> = {
  LOW_CONFIDENCE: '置信度低',
  MAX_RETRIES_EXCEEDED: '重试超限',
  USER_REQUESTED_HUMAN: '请求人工',
  COMPLEX_ISSUE: '复杂问题',
  SENTIMENT_NEGATIVE: '情绪负面',
  REPEATED_FAILURE: '重复失败',
};

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`;
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

interface ConversationItemProps {
  conversation: ConversationListItem;
  isSelected: boolean;
  onClick: () => void;
}

function ConversationItem({ conversation, isSelected, onClick }: ConversationItemProps) {
  const priority = priorityConfig[conversation.priority];
  const status = statusConfig[conversation.status];

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg transition-colors ${
        isSelected
          ? 'bg-blue-50 border border-blue-200'
          : 'hover:bg-gray-50 border border-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="font-medium text-gray-900 truncate">{conversation.userName}</span>
        <Badge variant={priority.variant} className="text-xs shrink-0">
          {priority.label}
        </Badge>
      </div>
      <p className="text-sm text-gray-500 truncate mb-1">{conversation.preview}</p>
      <div className="flex items-center justify-between text-xs">
        <span className={`${status.color} font-medium`}>{status.label}</span>
        <span className="text-gray-400">{formatTime(conversation.createdAt)}</span>
      </div>
      <div className="mt-1">
        <Badge variant="outline" className="text-xs text-gray-500">
          {reasonLabels[conversation.escalatedReason] || conversation.escalatedReason}
        </Badge>
      </div>
    </button>
  );
}

interface ConversationListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ConversationList({ selectedId, onSelect }: ConversationListProps) {
  const { conversations, loading, error, refetch } = useConversationList();

  if (loading && conversations.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-600 mb-2">{error}</p>
        <Button variant="outline" size="sm" onClick={refetch}>
          重试
        </Button>
      </div>
    );
  }

  const pendingCount = conversations.filter((c) => c.status === 'pending').length;
  const activeCount = conversations.filter((c) => c.status === 'active').length;

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-900">会话列表</h2>
          <Button variant="ghost" size="sm" onClick={refetch}>
            刷新
          </Button>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="text-amber-600 font-medium">待处理 {pendingCount}</span>
          <span className="text-gray-300">|</span>
          <span className="text-green-600 font-medium">进行中 {activeCount}</span>
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {conversations.length === 0 ? (
            <p className="text-center text-gray-500 py-8">暂无会话</p>
          ) : (
            conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isSelected={selectedId === conv.id}
                onClick={() => onSelect(conv.id)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
