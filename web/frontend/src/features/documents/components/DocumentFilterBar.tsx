import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import type { DocumentListParams, DocumentStatus } from '../types';

/**
 * Admin-only filter bar for the documents list. Department is intentionally
 * absent — the backend scopes results to the caller's own department from their
 * role, so exposing a department control here would be misleading.
 */
export interface DocumentFilters {
  filename: string;
  status: '' | DocumentStatus;
  mimeType: string;
  dateFrom: string;
  dateTo: string;
  version: string;
}

export const EMPTY_FILTERS: DocumentFilters = {
  filename: '',
  status: '',
  mimeType: '',
  dateFrom: '',
  dateTo: '',
  version: '',
};

/** MIME types the platform accepts (mirrors backend ALLOWED_MIME). */
const MIME_OPTIONS: Array<{ label: string; value: string }> = [
  { label: 'All types', value: '' },
  { label: 'PDF', value: 'application/pdf' },
  {
    label: 'DOCX',
    value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  },
  { label: 'TXT', value: 'text/plain' },
  { label: 'CSV', value: 'text/csv' },
  {
    label: 'XLSX',
    value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  },
];

const STATUS_OPTIONS: Array<{ label: string; value: '' | DocumentStatus }> = [
  { label: 'All statuses', value: '' },
  { label: 'Indexed', value: 'INDEXED' },
  { label: 'Pending', value: 'PENDING' },
  { label: 'Indexing', value: 'INDEXING' },
  { label: 'Failed', value: 'FAILED' },
];

interface Props {
  value: DocumentFilters;
  onChange: (next: DocumentFilters) => void;
  onReset: () => void;
}

export function DocumentFilterBar({ value, onChange, onReset }: Props) {
  const set = <K extends keyof DocumentFilters>(key: K, v: DocumentFilters[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <div className="mb-4 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6">
      <div className="lg:col-span-2">
        <label className="mb-1 block text-xs font-medium text-slate-500">Filename</label>
        <Input
          placeholder="Search by name…"
          value={value.filename}
          onChange={(e) => set('filename', e.target.value)}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500">Status</label>
        <Select
          value={value.status}
          onChange={(e) => set('status', e.target.value as '' | DocumentStatus)}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500">Type</label>
        <Select value={value.mimeType} onChange={(e) => set('mimeType', e.target.value)}>
          {MIME_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500">From</label>
        <Input
          type="date"
          value={value.dateFrom}
          onChange={(e) => set('dateFrom', e.target.value)}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500">To</label>
        <Input
          type="date"
          value={value.dateTo}
          onChange={(e) => set('dateTo', e.target.value)}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500">Version</label>
        <Input
          type="number"
          min={1}
          placeholder="Any"
          value={value.version}
          onChange={(e) => set('version', e.target.value)}
        />
      </div>

      <div className="flex items-end">
        <Button variant="outline" size="sm" onClick={onReset}>
          Reset
        </Button>
      </div>
    </div>
  );
}

/** Translate the UI filter state into API query params (dropping empties). */
export function filtersToParams(f: DocumentFilters): Omit<DocumentListParams, 'page' | 'pageSize'> {
  const params: Omit<DocumentListParams, 'page' | 'pageSize'> = {};
  if (f.filename.trim()) params.filename = f.filename.trim();
  if (f.status) params.status = f.status;
  if (f.mimeType) params.mimeType = f.mimeType;
  if (f.dateFrom) params.dateFrom = f.dateFrom;
  if (f.dateTo) params.dateTo = f.dateTo;
  if (f.version && Number(f.version) > 0) params.version = Number(f.version);
  return params;
}
