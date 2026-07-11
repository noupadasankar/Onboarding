import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  useListNotificationsQuery,
  useMarkReadMutation,
  useMarkAllReadMutation,
} from '../api/notificationsApi';

const PAGE_SIZE = 10;

export function NotificationsPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useListNotificationsQuery({ page, pageSize: PAGE_SIZE });
  const [markRead, { isLoading: isMarkingOne }] = useMarkReadMutation();
  const [markAllRead, { isLoading: isMarkingAll }] = useMarkAllReadMutation();

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const unreadCount = data?.unreadCount ?? 0;

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function truncate(text: string, max = 80) {
    return text.length <= max ? text : text.slice(0, max) + '…';
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Notifications</h1>
          <p className="text-sm text-slate-500">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
          </p>
        </div>
        <Button
          variant="outline"
          disabled={unreadCount === 0 || isMarkingAll}
          onClick={() => markAllRead()}
        >
          Mark all as read
        </Button>
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading notifications...</p>
      )}

      {isError && (
        <p className="py-8 text-center text-sm text-red-600">
          Failed to load notifications. Please try again.
        </p>
      )}

      {data && (
        <>
          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Title</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Body</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                      No notifications.
                    </td>
                  </tr>
                ) : (
                  data.items.map((n) => (
                    <tr
                      key={n.id}
                      className={`hover:bg-slate-50 ${!n.isRead ? 'bg-blue-50/40' : ''}`}
                    >
                      <td className="px-4 py-3 font-medium text-slate-900">{n.title}</td>
                      <td className="px-4 py-3 text-slate-600">{truncate(n.body)}</td>
                      <td className="px-4 py-3 text-slate-600">{n.type}</td>
                      <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                        {formatDate(n.createdAt)}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={n.isRead ? 'success' : 'warning'}>
                          {n.isRead ? 'Read' : 'Unread'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {!n.isRead && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={isMarkingOne}
                            onClick={() => markRead(n.id)}
                          >
                            Mark as read
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
                <span className="text-xs text-slate-500">
                  Page {page} of {totalPages} · {data.total} total
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
