/** Individual chat message component with markdown styling and citation badges. */
import type { ChatMessage as ChatMessageType, Citation } from '../types';
import { cn } from '@/lib/utils';
import { Bot, User, FileText } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
  onCitationClick?: (citation: Citation) => void;
}

export function ChatMessage({ message, isStreaming, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const time = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  // Render formatted markdown content
  const formatContent = (text: string) => {
    // Split into paragraphs / lines
    return text.split('\n').map((line, lineIdx) => {
      if (line.startsWith('### ')) {
        return (
          <h3 key={lineIdx} className="text-base font-bold text-slate-900 mt-2 mb-1 flex items-center gap-1.5">
            {line.replace('### ', '')}
          </h3>
        );
      }
      if (line.startsWith('#### ')) {
        return (
          <h4 key={lineIdx} className="text-sm font-semibold text-slate-800 mt-2 mb-1">
            {line.replace('#### ', '')}
          </h4>
        );
      }
      if (line.startsWith('- ') || line.startsWith('* ')) {
        const bulletText = line.substring(2);
        return (
          <li key={lineIdx} className="ml-4 list-disc text-sm text-slate-700 leading-relaxed">
            {renderBoldAndCode(bulletText)}
          </li>
        );
      }
      if (line.trim() === '') {
        return <div key={lineIdx} className="h-2" />;
      }
      return (
        <p key={lineIdx} className="text-sm leading-relaxed mb-1">
          {renderBoldAndCode(line)}
        </p>
      );
    });
  };

  const renderBoldAndCode = (str: string) => {
    // Handle ~~strikethrough~~
    const parts = str.split(/(~~.*?~~|\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('~~') && part.endsWith('~~')) {
        return <span key={i} className="line-through text-slate-400">{part.slice(2, -2)}</span>;
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="rounded bg-slate-100 px-1 py-0.5 text-xs font-mono text-teal-800">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-in group',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-xs font-medium shadow-sm',
          isUser
            ? 'bg-gradient-to-br from-teal-600 to-teal-700 text-white'
            : 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div className="flex flex-col max-w-[85%] md:max-w-[78%]">
        <div
          className={cn(
            'rounded-2xl px-4 py-3 shadow-xs',
            isUser
              ? 'bg-teal-700 text-white rounded-tr-xs'
              : 'bg-white border border-slate-200/80 text-slate-800 rounded-tl-xs'
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-white">{message.content}</p>
          ) : (
            <div>{formatContent(message.content)}</div>
          )}

          {isStreaming && (
            <span className="inline-block animate-pulse text-xs text-teal-600 ml-1">▌</span>
          )}

          {/* Citations Pill Bar */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <FileText className="h-3 w-3" /> Sources:
              </span>
              {message.citations.map((c, idx) => (
                <button
                  key={idx}
                  onClick={() => onCitationClick?.(c)}
                  className="inline-flex items-center gap-1 text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full transition-colors"
                >
                  <FileText className="h-2.5 w-2.5 text-teal-600" />
                  <span>{c.filename || 'Document'}</span>
                  {c.section && <span className="text-slate-400">§ {c.section}</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Time footer */}
        {time && (
          <span className={cn('text-[10px] text-slate-400 mt-1 px-1', isUser ? 'text-right' : 'text-left')}>
            {time}
          </span>
        )}
      </div>
    </div>
  );
}

