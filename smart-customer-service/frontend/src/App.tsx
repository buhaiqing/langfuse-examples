import { useState } from 'react';
import { ConversationList } from './components/conversation-list';
import { ConversationDetail } from './components/conversation-detail';
import { AgentStatusManager, AgentStatus } from './components/agent-status';
import { QuickReply } from './components/quick-reply';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Bell, Users, MessageSquare } from 'lucide-react';
import { wsClient } from './lib/websocket';
import type { WebSocketMessage } from './lib/websocket';

function App() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>();
  const [pendingEscalations, setPendingEscalations] = useState(0);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('online');

  useState(() => {
    wsClient.connect().catch(console.error);
    
    wsClient.on('escalation_request', handleEscalation);
    wsClient.on('new_message', handleNewMessage);

    return () => {
      wsClient.disconnect();
    };
  }, []);

  function handleEscalation(message: WebSocketMessage) {
    console.log('收到升级请求:', message);
    setPendingEscalations((prev) => prev + 1);
  }

  function handleNewMessage(message: WebSocketMessage) {
    console.log('收到新消息:', message);
  }

  function handleInsertReply(content: string) {
    // TODO: 将回复内容插入到会话详情的输入框
    console.log('插入回复:', content);
  }

  function handleStatusChange(status: AgentStatus) {
    console.log('状态变更:', status);
  }

  return (
    <div className="h-screen flex flex-col">
      <header className="h-14 border-b flex items-center justify-between px-4 bg-background">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold">智能客服工作台</h1>
          {pendingEscalations > 0 && (
            <Badge variant="destructive" className="animate-pulse">
              <Bell className="h-3 w-3 mr-1" />
              {pendingEscalations} 待处理
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* 快捷回复 */}
          <QuickReply onInsert={handleInsertReply} />
          
          {/* 客服状态 */}
          <AgentStatusManager
            agentId="agent_001"
            onStatusChange={handleStatusChange}
          />
          
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Users className="h-4 w-4" />
            <span>在线客服</span>
          </div>
          <Button variant="outline" size="sm">
            <MessageSquare className="h-4 w-4 mr-2" />
            统计
          </Button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-80 border-r">
          <ConversationList
            selectedId={selectedSessionId}
            onSelect={setSelectedSessionId}
          />
        </div>

        <div className="flex-1 p-4">
          {selectedSessionId ? (
            <ConversationDetail
              sessionId={selectedSessionId}
              onClose={() => setSelectedSessionId(undefined)}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>请从左侧选择一个会话</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
