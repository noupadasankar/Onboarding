import { Link } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Calendar, Clock, Ticket, Bell, MessageSquare } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const weeklyHours = [
  { day: 'Mon', hours: 8.5 },
  { day: 'Tue', hours: 7.8 },
  { day: 'Wed', hours: 9.0 },
  { day: 'Thu', hours: 8.2 },
  { day: 'Fri', hours: 7.5 },
];

const myTickets = [
  { id: 'INC-1042', title: 'VPN not connecting', status: 'In Progress', priority: 'High' },
  { id: 'INC-1035', title: 'Printer setup needed', status: 'Open', priority: 'Low' },
];

const announcements = [
  { title: 'Office closed on 14 July — Public Holiday', date: 'Jul 10' },
  { title: 'Performance review cycle opens 20 July', date: 'Jul 8' },
  { title: 'New expense policy effective Aug 1', date: 'Jul 5' },
];

const PRIORITY_PILL: Record<string, string> = {
  High:   'bg-red-100 text-red-700',
  Medium: 'bg-amber-100 text-amber-700',
  Low:    'bg-slate-100 text-slate-600',
};

const STATUS_PILL: Record<string, string> = {
  Open:        'bg-blue-100 text-blue-700',
  'In Progress':'bg-teal-100 text-teal-700',
  Resolved:    'bg-emerald-100 text-emerald-700',
};

export function EmployeeDashboard({ email }: { email: string }) {
  const name = (email.split('@')[0] ?? '').replace(/[._]/g, ' ');

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 capitalize">Welcome back, {name}</h1>
        <p className="text-sm text-slate-500">Employee Dashboard · July 2026</p>
      </div>

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Leave Balance</CardTitle>
            <Calendar className="h-4 w-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">12</p>
            <p className="mt-1 text-xs text-slate-400">days remaining</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Attendance</CardTitle>
            <Clock className="h-4 w-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">96%</p>
            <p className="mt-1 text-xs text-slate-400">this month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">My Tickets</CardTitle>
            <Ticket className="h-4 w-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">2</p>
            <p className="mt-1 text-xs text-slate-400">open tickets</p>
          </CardContent>
        </Card>
      </div>

      {/* AI Chat shortcuts */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Link to="/chat">
          <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:border-teal-400 hover:shadow-md">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">HR AI Chat</p>
              <p className="text-xs text-slate-500">Leave, salary, benefits, holidays</p>
            </div>
          </div>
        </Link>
        <Link to="/chat">
          <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-all hover:border-blue-400 hover:shadow-md">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">IT Support Chat</p>
              <p className="text-xs text-slate-500">Password reset, VPN, software help</p>
            </div>
          </div>
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Weekly hours chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Weekly Hours</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={weeklyHours} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="hoursGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0d9488" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[0, 12]} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Area type="monotone" dataKey="hours" stroke="#0d9488" strokeWidth={2} fill="url(#hoursGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* My Tickets */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">My Tickets</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">ID</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Issue</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Status</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {myTickets.map(t => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{t.id}</td>
                    <td className="px-4 py-3 text-slate-700">{t.title}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_PILL[t.status] ?? 'bg-slate-100 text-slate-600'}`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${PRIORITY_PILL[t.priority] ?? ''}`}>
                        {t.priority}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Announcements */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2 pb-3">
          <Bell className="h-4 w-4 text-amber-500" />
          <CardTitle className="text-sm font-semibold text-slate-800">Company Announcements</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {announcements.map(a => (
            <div key={a.title} className="flex items-start justify-between rounded-lg bg-slate-50 px-4 py-3">
              <p className="text-sm text-slate-700">{a.title}</p>
              <span className="ml-4 shrink-0 text-xs text-slate-400">{a.date}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
