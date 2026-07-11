import { useNavigate } from 'react-router-dom';
import { useListNotificationsQuery } from '../api/notificationsApi';

export function NotificationBell() {
  const navigate = useNavigate();
  const { data } = useListNotificationsQuery({ pageSize: 5 });
  const unreadCount = data?.unreadCount ?? 0;

  return (
    <button
      type="button"
      className="relative inline-flex items-center rounded-md p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
      onClick={() => navigate('/notifications')}
      aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
    >
      <span className="text-lg leading-none" aria-hidden="true">
        🔔
      </span>
      {unreadCount > 0 && (
        <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white leading-none">
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </button>
  );
}
