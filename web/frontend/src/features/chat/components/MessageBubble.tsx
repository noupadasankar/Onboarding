import type { MessageDTO } from '../types';

interface MessageBubbleProps {
  message: MessageDTO;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end" data-testid="user-message">
        <div className="max-w-[70%] rounded-l-2xl rounded-tr-2xl bg-teal-600 px-4 py-3 text-white">
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        </div>
      </div>
    );
  }

  const citations = message.citations?.filter(Boolean) ?? [];
  const hasStats = message.latencyMs != null || message.promptTokens != null || message.completionTokens != null;

  return (
    <div className="flex justify-start" data-testid="assistant-message">
      <div className="max-w-[70%]">
        <div className="rounded-r-2xl rounded-tl-2xl border border-slate-200 bg-white px-4 py-3">
          <p className="whitespace-pre-wrap text-sm text-slate-800">{message.content}</p>
        </div>

        {citations.length > 0 && (
          <div className="mt-1 space-y-0.5 px-1">
            {citations.map((citation, i) => (
              <p key={i} className="text-xs text-slate-400">
                {citation.filename}
                {citation.page != null ? `, p. ${citation.page}` : ''}
                {citation.section ? ` — ${citation.section}` : ''}
              </p>
            ))}
          </div>
        )}

        {hasStats && (
          <p className="mt-1 px-1 text-[11px] text-slate-300">
            {message.latencyMs != null && <span>{message.latencyMs}ms</span>}
            {message.promptTokens != null && (
              <span>
                {message.latencyMs != null ? ' · ' : ''}
                {message.promptTokens + (message.completionTokens ?? 0)} tokens
              </span>
            )}
          </p>
        )}
      </div>
    </div>
  );
}
