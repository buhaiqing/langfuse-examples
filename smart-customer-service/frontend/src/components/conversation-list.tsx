import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Filter, Clock, User } from 'lucide-react';
import type { Conversation } from '@/types';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ConversationListProps {
  selectedId?: string;
  onSelect: (id: string) => void;
}

export function ConversationList({ selectedId, onSelect }: ConversationListProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    loadConversations();
  }, []);

  async function loadConversations() {
    try {
      setLoading(true);
      const data = await api.conversations.list();
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  }

  const filteredConversations = conversations.filter((conv) => {
    const matchesSearch =
      conv.session_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conv.user_id.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesFilter = filter === 'all' || conv.priority_level === filter;

    return matchesSearch && matchesFilter;
  });

  // 按优先级排序
  const sortedConversations = [...filteredConversations].sort((a, b) => {
    const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    const aPriority = priorityOrder[a.priority_level || 'low'];
    const bPriority = priorityOrder[b.priority_level || 'low'];
    return aPriority - bPriority;
  });

  return (
    <Card className="w-full h-full flex flex-col">
      {/* 头部：搜索和筛选 */}
      <div className="p-4 border-b space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索会话..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex gap-2">
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
          >
            全部
          </Button>
          <Button
            variant={filter === 'critical' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('critical')}
          >
            紧急
          </Button>
          <Button
            variant={filter === 'high' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('high')}
          >
            高优
          </Button>
          <Button
            variant={filter === 'medium' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('medium')}
          >
            中
          </Button>
          <Button
            variant={filter === 'low' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('low')}
          >
            低
          </Button>
        </div>
      </div>

      {/* 会话列表 */}
      <ScrollArea className="flex-1">
        <div className="divide-y">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">加载中...</div>
          ) : sortedConversations.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">暂无会话</div>
          ) : (
            sortedConversations.map((conv) => (
              <button
                key={conv.session_id}
                onClick={() => onSelect(conv.session_id)}
                className={cn(
                  'w-full p-4 text-left hover:bg-accent transition-colors border-b last:border-b-0',
                  selectedId === conv.session_id && 'bg-accent'
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium text-sm truncate">{conv.user_id}</span>
                  </div>
                  {conv.priority_level && (
                    <Badge
                      variant={
                        conv.priority_level === 'critical'
                          ? 'destructive'
                          : conv.priority_level === 'high'
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {conv.priority_level === 'critical'
                        ? '紧急'
                        : conv.priority_level === 'high'
                        ? '高'
                        : conv.priority_level === 'medium'
                        ? '中'
                        : '低'}
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{formatTime(conv.updated_at)}</span>
                  </div>
                  <span>消息数：{conv.message_count}</span>
                  {conv.current_intent && <span>意图：{conv.current_intent}</span>}
                </div>
              </button>
            ))
          )}
        </div>
      </ScrollArea>

      {/* 底部刷新按钮 */}
      <div className="p-3 border-t">
        <Button variant="outline" size="sm" onClick={loadConversations} className="w-full">
          刷新
        </Button>
      </div>
    </Card>
  );
}

function formatTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  return `${days}天前`;
}
