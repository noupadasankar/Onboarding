import { Badge } from '@/components/ui/badge';
import type { DocumentStatus } from '../types';

const STATUS_CONFIG: Record<
  DocumentStatus,
  { variant: 'warning' | 'brand' | 'success' | 'danger' | 'default'; label: string }
> = {
  PENDING: { variant: 'warning', label: 'Pending' },
  INDEXING: { variant: 'brand', label: 'Indexing' },
  INDEXED: { variant: 'success', label: 'Indexed' },
  FAILED: { variant: 'danger', label: 'Failed' },
  SUPERSEDED: { variant: 'default', label: 'Superseded' },
  DELETED: { variant: 'default', label: 'Deleted' },
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const { variant, label } = STATUS_CONFIG[status] ?? { variant: 'default', label: status };
  return <Badge variant={variant}>{label}</Badge>;
}
