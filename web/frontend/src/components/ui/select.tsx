import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

// ─── Compound context ─────────────────────────────────────────────────────────

interface SelectCtxValue {
  value: string;
  onValueChange: (v: string) => void;
  open: boolean;
  setOpen: (v: boolean) => void;
  selectedLabel: string;
  setSelectedLabel: (v: string) => void;
}

const SelectCtx = createContext<SelectCtxValue | null>(null);

function useSelectCtx(): SelectCtxValue {
  const ctx = useContext(SelectCtx);
  if (!ctx) throw new Error('Select subcomponent must be inside <Select>');
  return ctx;
}

// ─── Types ────────────────────────────────────────────────────────────────────

type CompoundSelectProps = {
  value: string;
  onValueChange: (v: string) => void;
  children: ReactNode;
  className?: string;
};

type NativeSelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & {
  onValueChange?: undefined;
};

type SelectProps = CompoundSelectProps | NativeSelectProps;

// ─── Select (smart: compound when onValueChange provided, native otherwise) ───

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>((props, ref) => {
  const [open, setOpen] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Close compound dropdown on outside click (no-op in native mode — open is always false)
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (props.onValueChange !== undefined) {
    const { value, onValueChange, children, className } = props as CompoundSelectProps;
    return (
      <SelectCtx.Provider value={{ value, onValueChange, open, setOpen, selectedLabel, setSelectedLabel }}>
        <div ref={containerRef} className={cn('relative', className)}>
          {children}
        </div>
      </SelectCtx.Provider>
    );
  }

  const { onValueChange: _omit, ...nativeProps } = props as NativeSelectProps;
  return (
    <select
      ref={ref}
      className={cn(
        'flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-brand',
        'disabled:cursor-not-allowed disabled:opacity-50',
        nativeProps.className,
      )}
      {...nativeProps}
    />
  );
});
Select.displayName = 'Select';

// ─── SelectTrigger ────────────────────────────────────────────────────────────

export function SelectTrigger({ children, className }: { children: ReactNode; className?: string }) {
  const { open, setOpen } = useSelectCtx();
  return (
    <button
      type="button"
      onClick={() => setOpen(!open)}
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-md border border-slate-300 bg-white px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-brand',
        className,
      )}
      aria-expanded={open}
    >
      {children}
      <svg
        className="ml-2 h-4 w-4 shrink-0 opacity-50"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  );
}

// ─── SelectValue ─────────────────────────────────────────────────────────────

export function SelectValue({ placeholder }: { placeholder?: string }) {
  const { value, selectedLabel } = useSelectCtx();
  const display = value ? (selectedLabel || value) : '';
  return (
    <span className={display ? 'text-slate-900' : 'text-slate-400'}>
      {display || placeholder || ''}
    </span>
  );
}

// ─── SelectContent ────────────────────────────────────────────────────────────

// Rendered as hidden (not unmounted) so SelectItem effects fire and label is
// available in SelectValue from the first render.
export function SelectContent({ children }: { children: ReactNode }) {
  const { open } = useSelectCtx();
  return (
    <div
      className={cn(
        'absolute top-full z-50 mt-1 w-full rounded-md border border-slate-200 bg-white py-1 shadow-lg',
        !open && 'hidden',
      )}
    >
      {children}
    </div>
  );
}

// ─── SelectItem ──────────────────────────────────────────────────────────────

export function SelectItem({ value, children }: { value: string; children: ReactNode }) {
  const { value: selectedValue, onValueChange, setOpen, setSelectedLabel } = useSelectCtx();
  const isSelected = value === selectedValue;
  const label = typeof children === 'string' ? children : value;

  // Keep selectedLabel in sync so SelectValue shows the correct display text
  useEffect(() => {
    if (isSelected) setSelectedLabel(label);
  }, [isSelected, label, setSelectedLabel]);

  return (
    <button
      type="button"
      onClick={() => {
        onValueChange(value);
        setSelectedLabel(label);
        setOpen(false);
      }}
      className={cn(
        'flex w-full items-center px-3 py-2 text-sm hover:bg-slate-100',
        isSelected && 'bg-teal-50 font-medium text-teal-700',
      )}
    >
      {children}
    </button>
  );
}
