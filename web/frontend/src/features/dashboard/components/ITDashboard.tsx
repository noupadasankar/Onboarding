import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Ticket, AlertOctagon, Clock, Activity, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const ticketTrend = [
  { week: 'Wk 24', open: 38, closed: 45 },
  { week: 'Wk 25', open: 42, closed: 38 },
  { week: 'Wk 26', open: 51, closed: 49 },
  { week: 'Wk 27', open: 47, closed: 52 },
];

const servers = [
  { name: 'prod-api-01', status: 'Healthy', cpu: '34%', mem: '61%', uptime: '99.98%' },
  { name: 'prod-api-02', status: 'Healthy', cpu: '28%', mem: '55%', uptime: '99.97%' },
  { name: 'db-primary',  status: 'Healthy', cpu: '52%', mem: '78%', uptime: '100%'  },
  { name: 'db-replica',  status: 'Warning', cpu: '71%', mem: '88%', uptime: '99.41%' },
  { name: 'chroma-01',   status: 'Healthy', cpu: '18%', mem: '42%', uptime: '99.99%' },
];

const tickets = [
  { id: 'INC-1045', title: 'Database replica high memory', assignee: 'L. Osei', priority: 'Critical', status: 'Open' },
  { id: 'INC-1044', title: 'Email server timeout errors', assignee: 'M. Adusei', priority: 'High', status: 'In Progress' },
  { id: 'INC-1043', title: 'VPN client cert expired', assignee: 'L. Osei', priority: 'High', status: 'In Progress' },
  { id: 'INC-1042', title: 'Printer offline — 3rd floor', assignee: 'Unassigned', priority: 'Low', status: 'Open' },
];

const STATUS_ICON = {
  Healthy: <CheckCircle className="h-4 w-4 text-emerald-500" />,
  Warning: <AlertOctagon className="h-4 w-4 text-amber-500" />,
  Down:    <XCircle className="h-4 w-4 text-red-500" />,
};

const PRIORITY_PILL: Record<string, string> = {
  Critical: 'bg-red-100 text-red-700',
  High:     'bg-orange-100 text-orange-700',
  Medium:   'bg-amber-100 text-amber-700',
  Low:      'bg-slate-100 text-slate-600',
};

const TICKET_STATUS_PILL: Record<string, string> = {
  Open:          'bg-blue-100 text-blue-700',
  'In Progress': 'bg-teal-100 text-teal-700',
  Resolved:      'bg-emerald-100 text-emerald-700',
};

export function ITDashboard() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">IT Admin Dashboard</h1>
        <p className="text-sm text-slate-500">Infrastructure health & ticket management · July 2026</p>
      </div>

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Active Tickets</CardTitle>
            <Ticket className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">47</p>
            <p className="mt-1 text-xs text-slate-400">18 assigned today</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Critical Incidents</CardTitle>
            <AlertOctagon className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">3</p>
            <p className="mt-1 text-xs text-red-400 font-medium">Escalated</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">SLA Compliance</CardTitle>
            <Clock className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">94%</p>
            <p className="mt-1 text-xs text-slate-400">target: 95%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">System Uptime</CardTitle>
            <Activity className="h-4 w-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-teal-700">99.7%</p>
            <p className="mt-1 text-xs text-slate-400">last 30 days</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Ticket trend chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Ticket Volume Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={ticketTrend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Line type="monotone" dataKey="open" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4, fill: '#3b82f6' }} name="Opened" />
                <Line type="monotone" dataKey="closed" stroke="#10b981" strokeWidth={2} dot={{ r: 4, fill: '#10b981' }} name="Closed" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Server status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Server Health</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Server</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Status</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">CPU</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Mem</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Uptime</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {servers.map(s => (
                  <tr key={s.name} className={s.status === 'Warning' ? 'bg-amber-50' : 'hover:bg-slate-50'}>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-700">{s.name}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        {STATUS_ICON[s.status as keyof typeof STATUS_ICON] ?? STATUS_ICON.Healthy}
                        <span className={`text-xs font-medium ${s.status === 'Healthy' ? 'text-emerald-700' : s.status === 'Warning' ? 'text-amber-700' : 'text-red-700'}`}>
                          {s.status}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-600">{s.cpu}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-600">{s.mem}</td>
                    <td className="px-4 py-2.5 text-xs font-semibold text-slate-700">{s.uptime}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Ticket queue */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-slate-800">Ticket Queue</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">ID</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Issue</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Assignee</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Priority</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tickets.map(t => (
                <tr key={t.id} className={t.priority === 'Critical' ? 'bg-red-50' : 'hover:bg-slate-50'}>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{t.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">{t.title}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {t.assignee === 'Unassigned'
                      ? <span className="text-slate-400 italic">Unassigned</span>
                      : t.assignee
                    }
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${PRIORITY_PILL[t.priority] ?? ''}`}>
                      {t.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${TICKET_STATUS_PILL[t.status] ?? ''}`}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
