/**
 * Minimal, dependency-free toast system.
 *
 * Wrap a subtree in <ToastProvider>, then call useToast().showToast(...) from
 * anywhere inside it. Toasts auto-dismiss and stack in the bottom-right corner.
 * Kept intentionally small — no portals, no external libraries.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { cn } from '@/lib/utils';

export type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  /** Auto-dismiss delay in ms (default 6000). */
  durationMs?: number;
}

interface ToastItem extends ToastOptions {
  id: string;
}

interface ToastContextValue {
  showToast: (opts: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');
  return ctx;
}

const DEFAULT_DURATION = 6000;
const MAX_VISIBLE = 4;
let idCounter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const showToast = useCallback(
    (opts: ToastOptions) => {
      const id = `toast_${(idCounter += 1)}`;
      const item: ToastItem = { variant: 'info', ...opts, id };
      setToasts((prev) => [...prev, item].slice(-MAX_VISIBLE));
      const timer = setTimeout(() => dismiss(id), opts.durationMs ?? DEFAULT_DURATION);
      timers.current.set(id, timer);
    },
    [dismiss],
  );

  // Clear any pending timers on unmount.
  useEffect(() => {
    const map = timers.current;
    return () => {
      map.forEach((t) => clearTimeout(t));
      map.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

const VARIANT_STYLES: Record<ToastVariant, { container: string; icon: string; glyph: string }> = {
  success: { container: 'border-emerald-200 bg-emerald-50', icon: 'text-emerald-600', glyph: '✓' },
  error: { container: 'border-red-200 bg-red-50', icon: 'text-red-600', glyph: '✕' },
  warning: { container: 'border-amber-200 bg-amber-50', icon: 'text-amber-600', glyph: '!' },
  info: { container: 'border-slate-200 bg-white', icon: 'text-slate-500', glyph: 'i' },
};

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-80 flex-col gap-2"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((t) => {
        const styles = VARIANT_STYLES[t.variant ?? 'info'];
        return (
          <div
            key={t.id}
            role="status"
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-lg border p-3 shadow-lg',
              'animate-in fade-in slide-in-from-bottom-2',
              styles.container,
            )}
          >
            <span
              className={cn(
                'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                styles.icon,
              )}
              aria-hidden
            >
              {styles.glyph}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-slate-900">{t.title}</p>
              {t.description && (
                <p className="mt-0.5 break-words text-xs text-slate-600">{t.description}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onDismiss(t.id)}
              className="shrink-0 rounded p-0.5 text-slate-400 hover:text-slate-700"
              aria-label="Dismiss notification"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        );
      })}
    </div>
  );
}
