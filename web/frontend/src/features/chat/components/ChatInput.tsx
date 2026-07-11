import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface Department {
  name: string;
  displayName: string;
}

interface ChatInputProps {
  onSend: (question: string, departmentHint?: string) => void;
  isLoading: boolean;
  departments: Department[];
}

export function ChatInput({ onSend, isLoading, departments }: ChatInputProps) {
  const [question, setQuestion] = useState('');
  const [departmentHint, setDepartmentHint] = useState<string>('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setQuestion(e.target.value);
    autoResize();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed, departmentHint || undefined);
    setQuestion('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  const canSend = question.trim().length > 0 && !isLoading;

  return (
    <div className="border-t border-slate-200 bg-white p-4">
      <div className="flex items-end gap-3">
        <div className="w-44 flex-shrink-0">
          <Select value={departmentHint} onValueChange={setDepartmentHint}>
            <SelectTrigger className="h-9 text-sm">
              <SelectValue placeholder="All departments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All departments</SelectItem>
              {departments.map((d) => (
                <SelectItem key={d.name} value={d.name}>
                  {d.displayName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <textarea
          ref={textareaRef}
          value={question}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question…"
          rows={1}
          className="flex-1 resize-none overflow-y-auto rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          style={{ maxHeight: 120 }}
        />

        <Button
          onClick={submit}
          disabled={!canSend}
          className="flex-shrink-0"
        >
          {isLoading ? 'Thinking…' : 'Send'}
        </Button>
      </div>
    </div>
  );
}
