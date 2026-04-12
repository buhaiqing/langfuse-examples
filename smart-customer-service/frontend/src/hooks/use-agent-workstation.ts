import { useState, useEffect, useCallback } from 'react';
import type {
  Conversation,
  ConversationListItem,
  SendMessageRequest,
  ApiResponse,
} from '@/types/agent-workstation';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

function convertConversation(data: any): Conversation {
  return {
    id: data.id,
    sessionId: data.session_id,
    userId: data.user_id,
    userName: data.user_name,
    userEmail: data.user_email,
    status: data.status,
    priority: data.priority,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
    resolvedAt: data.resolved_at,
    escalatedAt: data.escalated_at,
    escalatedReason: data.escalated_reason,
    escalatedReasonDescription: data.escalated_reason_description,
    messages: (data.messages || []).map((msg: any) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp,
      metadata: msg.metadata,
    })),
    context: data.context
      ? {
          totalTurns: data.context.total_turns,
          aiResolutionAttempts: data.context.ai_resolution_attempts,
          lastIntent: data.context.last_intent,
          lastConfidence: data.context.last_confidence,
        }
      : undefined,
    assignedAgent: data.assigned_agent
      ? {
          id: data.assigned_agent.id,
          name: data.assigned_agent.name,
        }
      : undefined,
  };
}

function convertConversationListItem(data: any): ConversationListItem {
  return {
    id: data.id,
    sessionId: data.session_id,
    userName: data.user_name,
    status: data.status,
    priority: data.priority,
    preview: data.preview,
    createdAt: data.created_at,
    escalatedReason: data.escalated_reason,
  };
}

export function useConversationList() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchApi<ApiResponse<{ conversations: any[] }>>('/api/conversations');
      if (response.success && response.data) {
        const converted = response.data.conversations.map(convertConversationListItem);
        setConversations(converted);
      } else {
        setError(response.error || '获取会话列表失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取会话列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, 30000);
    return () => clearInterval(interval);
  }, [fetchConversations]);

  return { conversations, loading, error, refetch: fetchConversations };
}

export function useConversation(conversationId: string | null) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchConversation = useCallback(async () => {
    if (!conversationId) return;
    try {
      setLoading(true);
      setError(null);
      const response = await fetchApi<ApiResponse<{ conversation: any }>>(
        `/api/conversations/${conversationId}`
      );
      if (response.success && response.data) {
        setConversation(convertConversation(response.data.conversation));
      } else {
        setError(response.error || '获取会话详情失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取会话详情失败');
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    fetchConversation();
  }, [fetchConversation]);

  return { conversation, loading, error, refetch: fetchConversation };
}

export function useSendMessage() {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (
    request: SendMessageRequest
  ): Promise<ApiResponse<{ messageId: string }>> => {
    try {
      setSending(true);
      setError(null);
      const response = await fetchApi<ApiResponse<{ message_id: string }>>(
        `/api/conversations/${request.conversationId}/messages`,
        {
          method: 'POST',
          body: JSON.stringify({ content: request.content, agent_id: 'agent-1' }),
        }
      );
      return {
        success: response.success,
        data: response.success ? { messageId: response.data?.message_id || '' } : undefined,
        error: response.error,
      };
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '发送消息失败';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setSending(false);
    }
  };

  return { sendMessage, sending, error };
}

export function useResolveConversation() {
  const [resolving, setResolving] = useState(false);

  const resolveConversation = async (
    conversationId: string
  ): Promise<ApiResponse<void>> => {
    try {
      setResolving(true);
      const response = await fetchApi<ApiResponse<void>>(
        `/api/conversations/${conversationId}/resolve`,
        {
          method: 'POST',
          body: JSON.stringify({}),
        }
      );
      return response;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : '解决会话失败',
      };
    } finally {
      setResolving(false);
    }
  };

  return { resolveConversation, resolving };
}

export { API_BASE_URL };
