/**
 * 快捷回复组件
 * 
 * 功能：
 * - 回复模板管理
 * - 模板快捷插入
 * - 常用回复分类
 * - 个性化模板
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { MessageSquare, Search, Plus, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ReplyTemplate {
  id: string;
  title: string;
  content: string;
  category: 'greeting' | 'troubleshooting' | 'closing' | 'custom';
  isFavorite?: boolean;
}

interface QuickReplyProps {
  onInsert: (content: string) => void;
  templates?: ReplyTemplate[];
}

const DEFAULT_TEMPLATES: ReplyTemplate[] = [
  {
    id: '1',
    title: '问候语',
    content: '您好！我是智能客服助手，很高兴为您服务。请问有什么可以帮您的吗？',
    category: 'greeting',
    isFavorite: true,
  },
  {
    id: '2',
    title: '问题确认',
    content: '请您详细描述一下遇到的问题，包括错误提示、操作步骤等，这样我可以更好地帮助您。',
    category: 'troubleshooting',
  },
  {
    id: '3',
    title: '感谢用语',
    content: '感谢您的耐心等待，我会尽快为您处理这个问题。',
    category: 'greeting',
  },
  {
    id: '4',
    title: '转人工',
    content: '您的问题比较复杂，我将为您转接专业客服人员，请稍等。',
    category: 'closing',
  },
  {
    id: '5',
    title: '结束语',
    content: '感谢您的咨询，如果还有其他问题，欢迎随时联系我们。祝您生活愉快！',
    category: 'closing',
  },
];

export function QuickReply({ onInsert, templates = [] }: QuickReplyProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [allTemplates, setAllTemplates] = useState<ReplyTemplate[]>([]);

  useEffect(() => {
    // 合并默认模板和自定义模板
    setAllTemplates([...DEFAULT_TEMPLATES, ...templates]);
  }, [templates]);

  const filteredTemplates = allTemplates.filter((template) => {
    const matchesSearch =
      template.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.content.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory =
      selectedCategory === 'all' || template.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const categories = [
    { id: 'all', label: '全部', count: allTemplates.length },
    { id: 'greeting', label: '问候语', count: allTemplates.filter((t) => t.category === 'greeting').length },
    { id: 'troubleshooting', label: '问题处理', count: allTemplates.filter((t) => t.category === 'troubleshooting').length },
    { id: 'closing', label: '结束语', count: allTemplates.filter((t) => t.category === 'closing').length },
    { id: 'custom', label: '自定义', count: allTemplates.filter((t) => t.category === 'custom').length },
  ];

  const handleInsert = (template: ReplyTemplate) => {
    onInsert(template.content);
    setIsOpen(false);
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <MessageSquare className="h-4 w-4" />
          快捷回复
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <div className="flex flex-col">
          {/* 搜索框 */}
          <div className="p-3 border-b">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索回复模板..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>

          {/* 分类筛选 */}
          <div className="p-2 border-b flex gap-1 flex-wrap">
            {categories.map((category) => (
              <Badge
                key={category.id}
                variant={selectedCategory === category.id ? 'default' : 'outline'}
                className="cursor-pointer text-xs"
                onClick={() => setSelectedCategory(category.id)}
              >
                {category.label} ({category.count})
              </Badge>
            ))}
          </div>

          {/* 模板列表 */}
          <ScrollArea className="h-[300px]">
            <div className="divide-y">
              {filteredTemplates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => handleInsert(template)}
                  className={cn(
                    'w-full p-3 text-left hover:bg-accent transition-colors',
                    'border-b last:border-b-0'
                  )}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="font-medium text-sm">{template.title}</span>
                    {template.isFavorite && (
                      <Badge variant="secondary" className="text-xs">
                        ⭐ 常用
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {template.content}
                  </p>
                </button>
              ))}
            </div>
          </ScrollArea>

          {/* 底部统计 */}
          <div className="p-2 border-t text-xs text-muted-foreground flex justify-between">
            <span>共 {filteredTemplates.length} 个模板</span>
            <Button variant="ghost" size="sm" className="h-6 text-xs">
              <Plus className="h-3 w-3 mr-1" />
              新建模板
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
