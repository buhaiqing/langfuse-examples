export type MessageRole = 'user' | 'assistant' | 'agent' | 'system';

export type ConversationStatus = 'active' | 'pending' | 'resolved' | 'closed';

export type EscalationReason =
  | 'LOW_CONFIDENCE'
  | 'MAX_RETRIES_EXCEEDED'
  | 'USER_REQUESTED_HUMAN'
  | 'COMPLEX_ISSUE'
  | 'SENTIMENT_NEGATIVE'
  | 'REPEATED_FAILURE';

export type Priority = 'low' | 'medium' | 'high' | 'urgent';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  metadata?: {
    intent?: string;
    confidence?: number;
    sentiment?: number;
  };
}

export interface Conversation {
  id: string;
  sessionId: string;
  userId: string;
  userName?: string;
  userEmail?: string;
  status: ConversationStatus;
  priority: Priority;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  escalatedAt: string;
  escalatedReason: EscalationReason;
  escalatedReasonDescription: string;
  messages: Message[];
  context?: {
    totalTurns: number;
    aiResolutionAttempts: number;
    lastIntent?: string;
    lastConfidence?: number;
  };
  assignedAgent?: {
    id: string;
    name: string;
  };
}

export interface Agent {
  id: string;
  name: string;
  email: string;
  status: 'online' | 'away' | 'busy' | 'offline';
  activeConversations: number;
  maxConversations: number;
}

export interface ConversationListItem {
  id: string;
  sessionId: string;
  userName: string;
  status: ConversationStatus;
  priority: Priority;
  preview: string;
  createdAt: string;
  escalatedReason: EscalationReason;
}

export interface SendMessageRequest {
  conversationId: string;
  content: string;
}

export interface EscalationWebhookPayload {
  event: 'escalation_required';
  session_id: string;
  reason: EscalationReason;
  confidence_score: number;
  suggested_action: string;
  timestamp: string;
  priority: Priority;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}
