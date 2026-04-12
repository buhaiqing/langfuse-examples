import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { useConversation } from '@/hooks/use-agent-workstation';
import type { Message, Priority, ConversationStatus } from '@/types/agent-workstation';

const priorityConfig: Record<Priority, { label: string; variant: 'destructive' | 'secondary' | 'outline' }> = {
  urgent: { label: '紧急', variant: 'destructive' },
  high: { label: '高', variant: 'secondary' },
  medium: { label: '中', variant: 'secondary' },
  low: { label: '低', variant: 'outline' },
};

const statusConfig: Record<ConversationStatus, { label: string; bgColor: string; textColor: string }> = {
  pending: { label: '待处理', bgColor: 'bg-amber-100', textColor: 'text-amber-800' },
  active: { label: '进行中', bgColor: 'bg-green-100', textColor: 'text-green-800' },
  resolved: { label: '已解决', bgColor: 'bg-gray-100', textColor: 'text-gray-600' },
  closed: { label: '已关闭', bgColor: 'bg-gray-200', textColor: 'text-gray-500' },
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
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(startIso: string, endIso?: string): string {
  const start = new Date(startIso);
  const end = endIso ? new Date(endIso) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}分钟`;
  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  return `${hours}小时${mins}分钟`;
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const isAgent = message.role === 'agent';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-blue-500 text-white'
            : isAgent
            ? 'bg-green-100 text-gray-900'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="text-xs opacity-70 mb-1">
          {isUser ? '用户' : isAgent ? '人工客服' : 'AI客服'}
        </div>
        <p className="whitespace-pre-wrap">{message.content}</p>
        <div className="text-xs opacity-70 text-right mt-1">
          {formatTime(message.timestamp)}
        </div>
        {message.metadata && (
          <div className="mt-1 flex gap-1 flex-wrap">
            {message.metadata.intent && (
              <Badge variant="outline" className="text-xs">
                {message.metadata.intent}
              </Badge>
            )}
            {message.metadata.confidence !== undefined && (
              <Badge variant="outline" className="text-xs">
                置信度: {message.metadata.confidence.toFixed(2)}
              </Badge>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface ConversationDetailProps {
  conversationId: string | null;
  onResolve: (id: string) => void;
}

export function ConversationDetail({ conversationId, onResolve }: ConversationDetailProps) {
  const { conversation, loading, error } = useConversation(conversationId);

  if (!conversationId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        选择一个会话查看详情
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner />
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className="flex items-center justify-center h-full text-red-600">
        {error || '加载失败'}
      </div>
    );
  }

  const priority = priorityConfig[conversation.priority];
  const status = statusConfig[conversation.status];
  const duration = formatDuration(conversation.createdAt, conversation.resolvedAt);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{conversation.userName}</h2>
            <p className="text-sm text-gray-500">{conversation.userEmail}</p>
          </div>
          <div className="flex gap-2">
            <Badge variant={priority.variant}>{priority.label}</Badge>
            <Badge className={`${status.bgColor} ${status.textColor}`}>{status.label}</Badge>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">会话ID:</span>
            <span className="ml-1 text-gray-900 font-mono text-xs">{conversation.sessionId}</span>
          </div>
          <div>
            <span className="text-gray-500">转接原因:</span>
            <span className="ml-1 text-gray-900">
              {reasonLabels[conversation.escalatedReason] || conversation.escalatedReason}
            </span>
          </div>
          <div>
            <span className="text-gray-500">等待时长:</span>
            <span className="ml-1 text-amber-600 font-medium">{duration}</span>
          </div>
          <div>
            <span className="text-gray-500">会话轮次:</span>
            <span className="ml-1 text-gray-900">{conversation.context?.totalTurns || 0}</span>
          </div>
        </div>

        {conversation.escalatedReasonDescription && (
          <div className="mt-2 p-2 bg-amber-50 rounded text-sm text-amber-800">
            <span className="font-medium">转接说明:</span> {conversation.escalatedReasonDescription}
          </div>
        )}

        {conversation.assignedAgent && (
          <div className="mt-2 text-sm text-gray-500">
            <span>当前客服:</span>
            <span className="ml-1 text-gray-900 font-medium">{conversation.assignedAgent.name}</span>
          </div>
        )}

        <div className="flex gap-2 mt-3">
          <Button
            size="sm"
            disabled={conversation.status === 'resolved' || conversation.status === 'closed'}
            onClick={() => onResolve(conversation.id)}
          >
            标记已解决
          </Button>
          <Button size="sm" variant="outline">
            转移会话
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-1">
          {conversation.messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
