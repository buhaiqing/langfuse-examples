import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Send, Bot, User, Clock, AlertCircle } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import type { Conversation, Message, IntentResult } from '@/types';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ConversationDetailProps {
  sessionId: string;
  onClose: () => void;
}

export function ConversationDetail({ sessionId, onClose }: ConversationDetailProps) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (sessionId) {
      loadConversation();
    }
  }, [sessionId]);

  async function loadConversation() {
    try {
      setLoading(true);
      const [convData, historyData] = await Promise.all([
        api.conversations.get(sessionId),
        // TODO: 添加获取历史消息的 API
      ]);
      
      setConversation(convData);
      // Mock 消息数据
      setMessages([
        {
          id: '1',
          session_id: sessionId,
          role: 'user',
          content: '我的 API 返回 403 错误',
          timestamp: new Date().toISOString(),
        },
        {
          id: '2',
          session_id: sessionId,
          role: 'assistant',
          content: '您好！403 错误通常表示权限不足。请问您能提供更多详细信息吗？',
          timestamp: new Date().toISOString(),
          intent: {
            intent: 'api_error_troubleshooting',
            confidence: 0.92,
            slots: { error_code: '403' },
            entities: [{ type: 'error_code', value: '403' }],
          },
        },
      ]);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage() {
    if (!inputMessage.trim() || sending) return;

    try {
      setSending(true);
      const message = inputMessage.trim();
      setInputMessage('');

      // 添加用户消息到本地
      const newUserMessage: Message = {
        id: `new-${Date.now()}`,
        session_id: sessionId,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, newUserMessage]);

      // 调用 API 发送消息
      await api.conversations.addMessage(sessionId, 'user', message);

      // TODO: 调用意图识别和 AI 回复
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSending(false);
    }
  }

  function getIntentBadge(intent: IntentResult | undefined) {
    if (!intent) return null;

    return (
      <div className="flex items-center gap-2 mt-2 text-xs">
        <Badge variant="outline" className="bg-blue-50">
          {intent.intent.replace(/_/g, ' ')}
        </Badge>
        <span className="text-muted-foreground">置信度：{(intent.confidence * 100).toFixed(0)}%</span>
        {Object.keys(intent.slots).length > 0 && (
          <span className="text-muted-foreground">
            槽位：{Object.entries(intent.slots)
              .map(([k, v]) => `${k}=${v}`)
              .join(', ')}
          </span>
        )}
      </div>
    );
  }

  if (loading) {
    return (
      <Card className="w-full h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">加载中...</div>
      </Card>
    );
  }

  if (!conversation) {
    return (
      <Card className="w-full h-full flex items-center justify-center">
        <div className="text-center text-muted-foreground">会话不存在</div>
      </Card>
    );
  }

  return (
    <Card className="w-full h-full flex flex-col">
      {/* 头部 */}
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Avatar className="h-10 w-10">
            <div className="bg-primary text-primary-foreground flex items-center justify-center h-full w-full">
              <User className="h-6 w-6" />
            </div>
          </Avatar>
          <div>
            <div className="font-semibold">{conversation.user_id}</div>
            <div className="text-xs text-muted-foreground">
              会话 ID: {conversation.session_id}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {conversation.priority_level && (
            <Badge
              variant={
                conversation.priority_level === 'critical'
                  ? 'destructive'
                  : conversation.priority_level === 'high'
                  ? 'default'
                  : 'secondary'
              }
            >
              {conversation.priority_level === 'critical'
                ? '紧急'
                : conversation.priority_level === 'high'
                ? '高'
                : conversation.priority_level === 'medium'
                ? '中'
                : '低'}
            </Badge>
          )}
          <Button variant="ghost" size="sm" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>

      {/* 消息列表 */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn('flex items-start gap-3', message.role === 'user' ? 'flex-row-reverse' : '')}
            >
              <Avatar className="h-8 w-8">
                {message.role === 'assistant' || message.role === 'agent' ? (
                  <div className="bg-blue-500 flex items-center justify-center h-full w-full">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                ) : (
                  <div className="bg-gray-500 flex items-center justify-center h-full w-full">
                    <User className="h-5 w-5 text-white" />
                  </div>
                )}
              </Avatar>

              <div className={cn('max-w-[70%]', message.role === 'user' ? 'text-right' : '')}>
                <Card
                  className={cn(
                    'p-3',
                    message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-background'
                  )}
                >
                  <p className="text-sm">{message.content}</p>
                </Card>

                {/* 意图信息（仅 AI 消息显示） */}
                {(message.role === 'assistant' || message.role === 'agent') && message.intent && (
                  <div className={cn('mt-2', message.role === 'user' ? 'text-right' : '')}>
                    {getIntentBadge(message.intent)}
                  </div>
                )}

                <div className={cn('flex items-center gap-1 mt-1 text-xs text-muted-foreground', message.role === 'user' ? 'justify-end' : '')}>
                  <Clock className="h-3 w-3" />
                  <span>{formatMessageTime(message.timestamp)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* 意图可视化区域 */}
      {conversation.current_intent && (
        <div className="p-3 border-t bg-muted/50">
          <div className="flex items-center gap-2 text-sm">
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">当前意图:</span>
            <Badge variant="outline">{conversation.current_intent.replace(/_/g, ' ')}</Badge>
            {Object.keys(conversation.collected_slots).length > 0 && (
              <span className="text-muted-foreground">
                已收集槽位：{Object.entries(conversation.collected_slots)
                  .map(([k, v]) => `${k}=${v}`)
                  .join(', ')}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 消息输入 */}
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <Textarea
            placeholder="输入回复内容..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            className="min-h-[60px] resize-none"
            disabled={sending}
          />
          <Button onClick={sendMessage} disabled={sending || !inputMessage.trim()} className="self-end">
            <Send className="h-4 w-4 mr-2" />
            发送
          </Button>
        </div>
        <div className="text-xs text-muted-foreground mt-2">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>
    </Card>
  );
}

function formatMessageTime(dateString: string): string {
  const date = new Date(dateString);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}
