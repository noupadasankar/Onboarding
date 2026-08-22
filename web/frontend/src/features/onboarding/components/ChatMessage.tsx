/** Individual chat message component. */
import type { ChatMessage } from '../types';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const time = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-in',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        )}
      >
        {isUser ? 'U' : 'AI'}
      </div>
      <div
        className={cn(
          'max-w-[70%] rounded-2xl px-4 py-2',
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-none'
            : 'bg-muted rounded-tl-none'
        )}
      >
        <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        {time && (
          <p className={cn('text-xs mt-1 opacity-70', isUser ? 'text-right' : '')}>
            {time}
          </p>
        )}
        {isStreaming && (
          <span className="inline-block animate-pulse text-xs opacity-50">▌</span>
        )}
      </div>
    </div>
  );
}
