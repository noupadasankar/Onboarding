import { Button } from '@/components/ui/button';
import type { ConversationDTO } from '../types';

interface ConversationSidebarProps {
  conversations: ConversationDTO[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  isLoading: boolean;
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  isLoading,
}: ConversationSidebarProps) {
  return (
    <div className="flex h-full w-64 flex-shrink-0 flex-col border-r border-slate-200 bg-slate-50">
      <div className="p-3">
        <Button className="w-full" onClick={onNew}>
          New conversation
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <p className="px-4 py-3 text-sm text-slate-400">Loading…</p>
        )}
        {!isLoading && conversations.length === 0 && (
          <p className="px-4 py-3 text-sm text-slate-400">No conversations yet.</p>
        )}
        {conversations.map((conv) => {
          const isActive = conv.id === activeId;
          return (
            <button
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              className={[
                'w-full px-4 py-3 text-left transition-colors',
                isActive
                  ? 'bg-teal-50 border-r-2 border-teal-600'
                  : 'hover:bg-slate-100',
              ].join(' ')}
            >
              <p
                className={[
                  'truncate text-sm font-medium',
                  isActive ? 'text-teal-700' : 'text-slate-800',
                ].join(' ')}
              >
                {conv.title ?? 'Untitled conversation'}
              </p>
              <p className="mt-0.5 text-xs text-slate-400">
                {new Date(conv.updatedAt).toLocaleDateString()}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
