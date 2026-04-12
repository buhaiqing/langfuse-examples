import { Badge } from '@/components/ui/badge';

const quickReplies = [
  { id: 'greeting', text: '您好，请问有什么可以帮助您的？' },
  { id: 'wait', text: '请稍等，我帮您查询一下。' },
  { id: 'understand', text: '我理解您的问题。' },
  { id: 'follow', text: '请问还有其他问题吗？' },
  { id: 'thanks', text: '感谢您的来电，再见！' },
  { id: 'escalate', text: '这个问题我需要转接专业客服为您处理。' },
];

interface QuickRepliesProps {
  onSelect: (text: string) => void;
}

export function QuickReplies({ onSelect }: QuickRepliesProps) {
  return (
    <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-gray-500 shrink-0">快捷回复:</span>
        {quickReplies.map((reply) => (
          <Badge
            key={reply.id}
            variant="secondary"
            className="cursor-pointer hover:bg-gray-200 transition-colors text-xs"
            onClick={() => onSelect(reply.text)}
          >
            {reply.text.length > 15 ? `${reply.text.slice(0, 15)}...` : reply.text}
          </Badge>
        ))}
      </div>
    </div>
  );
}
