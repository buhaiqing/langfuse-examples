import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Spinner } from '@/components/ui/spinner';
import { useSendMessage } from '@/hooks/use-agent-workstation';

interface MessageInputProps {
  conversationId: string;
  disabled?: boolean;
  onMessageSent?: () => void;
}

export function MessageInput({ conversationId, disabled, onMessageSent }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage } = useSendMessage();

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSend = async () => {
    if (!message.trim() || sending || disabled) return;

    setSending(true);
    const result = await sendMessage({
      conversationId,
      content: message.trim(),
    });

    if (result.success) {
      setMessage('');
      onMessageSent?.();
    }
    setSending(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isDisabled = disabled || sending || !message.trim();

  return (
    <div className="p-4 border-t border-gray-200 bg-white">
      <div className="flex gap-2">
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入回复内容，按 Enter 发送..."
          className="min-h-[44px] max-h-[120px] resize-none"
          disabled={disabled}
        />
        <Button
          onClick={handleSend}
          disabled={isDisabled}
          className="self-end shrink-0"
        >
          {sending ? <Spinner /> : '发送'}
        </Button>
      </div>
      <div className="mt-2 flex justify-between text-xs text-gray-400">
        <span>Enter 发送，Shift + Enter 换行</span>
        <span>{message.length} 字符</span>
      </div>
    </div>
  );
}
