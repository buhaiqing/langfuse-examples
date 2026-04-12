import { useState } from 'react';
import { ConversationList } from './ConversationList';
import { ConversationDetail } from './ConversationDetail';
import { MessageInput } from './MessageInput';
import { QuickReplies } from './QuickReplies';
import { AgentStatus } from './AgentStatus';
import { useResolveConversation } from '@/hooks/use-agent-workstation';

const mockAgent = {
  name: '客服小王',
  status: 'online' as const,
  activeConversations: 3,
  maxConversations: 5,
};

export function AgentWorkstation() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { resolveConversation, resolving } = useResolveConversation();

  const handleSelect = (id: string) => {
    setSelectedId(id);
  };

  const handleResolve = async (id: string) => {
    const result = await resolveConversation(id);
    if (result.success) {
      setSelectedId(null);
      setRefreshKey((k) => k + 1);
    }
  };

  const handleQuickReply = (text: string) => {
    console.log('Quick reply selected:', text);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <AgentStatus agent={mockAgent} />

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-80 bg-white border-r border-gray-200 flex flex-col">
          <ConversationList
            key={refreshKey}
            selectedId={selectedId}
            onSelect={handleSelect}
          />
        </aside>

        <main className="flex-1 flex flex-col bg-white">
          <ConversationDetail
            conversationId={selectedId}
            onResolve={handleResolve}
          />
          {selectedId && (
            <>
              <QuickReplies onSelect={handleQuickReply} />
              <MessageInput
                conversationId={selectedId}
                disabled={resolving}
                onMessageSent={() => setRefreshKey((k) => k + 1)}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
}
