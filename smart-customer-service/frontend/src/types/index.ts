/**
 * 类型定义
 */

export interface Conversation {
  session_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  current_intent: string | null;
  collected_slots: Record<string, any>;
  message_count: number;
  priority_level?: 'critical' | 'high' | 'medium' | 'low';
  status: 'active' | 'pending' | 'resolved' | 'escalated';
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'agent';
  content: string;
  timestamp: string;
  intent?: IntentResult;
  metadata?: Record<string, any>;
}

export interface IntentResult {
  intent: string;
  confidence: number;
  slots: Record<string, any>;
  entities: Array<{ type: string; value: string }>;
}

export interface AgentStatus {
  agent_id: string;
  status: 'online' | 'busy' | 'away' | 'offline';
  concurrent_chats: number;
  max_concurrent_chats: number;
}

export interface EscalationRequest {
  session_id: string;
  user_id: string;
  priority_score: number;
  priority_level: 'critical' | 'high' | 'medium' | 'low';
  trigger_reasons: string[];
  created_at: string;
}
