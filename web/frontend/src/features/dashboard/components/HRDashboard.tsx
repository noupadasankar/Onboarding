import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Users, CalendarCheck, Briefcase, TrendingDown, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const deptDistribution = [
  { dept: 'Engineering', count: 82 },
  { dept: 'HR', count: 18 },
  { dept: 'Finance', count: 24 },
  { dept: 'Sales', count: 56 },
  { dept: 'Operations', count: 68 },
];

const attendanceTrend = [
  { month: 'Feb', pct: 91 },
  { month: 'Mar', pct: 94 },
  { month: 'Apr', pct: 93 },
  { month: 'May', pct: 96 },
  { month: 'Jun', pct: 95 },
  { month: 'Jul', pct: 97 },
];

const leaveRequests = [
  { name: 'Alice Mensah',    type: 'Annual',  days: 5, status: 'Pending' },
  { name: 'Ben Okafor',      type: 'Sick',    days: 2, status: 'Pending' },
  { name: 'Clara Nwosu',     type: 'Annual',  days: 3, status: 'Approved' },
  { name: 'David Asante',    type: 'Maternity', days: 90, status: 'Approved' },
];

const governanceAlerts = [
  { msg: 'AI answer confidence < 70% for salary query', severity: 'warn' },
  { msg: 'Leave rejection rate spike in Engineering dept', severity: 'warn' },
  { msg: 'Resume screening completed for 12 candidates', severity: 'info' },
];

const STATUS_PILL: Record<string, string> = {
  Pending:  'bg-amber-100 text-amber-700',
  Approved: 'bg-emerald-100 text-emerald-700',
  Rejected: 'bg-red-100 text-red-700',
};

export function HRDashboard() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">HR Manager Dashboard</h1>
        <p className="text-sm text-slate-500">People analytics & workforce management · July 2026</p>
      </div>

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Total Employees</CardTitle>
            <Users className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">248</p>
            <p className="mt-1 text-xs text-slate-400">+4 this month</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Leave Requests</CardTitle>
            <CalendarCheck className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">12</p>
            <p className="mt-1 text-xs text-amber-500 font-medium">8 pending review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Open Positions</CardTitle>
            <Briefcase className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">5</p>
            <p className="mt-1 text-xs text-slate-400">across 3 departments</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Attrition Rate</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">3.2%</p>
            <p className="mt-1 text-xs text-slate-400">rolling 12 months</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Dept distribution bar chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Headcount by Department</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={deptDistribution} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dept" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} name="Employees" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Attendance trend line chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Attendance Trend (%)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={attendanceTrend} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[85, 100]} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Line type="monotone" dataKey="pct" stroke="#10b981" strokeWidth={2} dot={{ r: 4, fill: '#10b981' }} name="Attendance %" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Leave approval table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-slate-800">Leave Requests</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Employee</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Type</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Days</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Status</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {leaveRequests.map(r => (
                <tr key={r.name} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-800">{r.name}</td>
                  <td className="px-4 py-3 text-slate-600">{r.type}</td>
                  <td className="px-4 py-3 text-slate-600">{r.days}d</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_PILL[r.status] ?? ''}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {r.status === 'Pending' && (
                      <div className="flex items-center gap-2">
                        <button className="flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700 transition-colors hover:bg-emerald-100">
                          <CheckCircle className="h-3 w-3" /> Approve
                        </button>
                        <button className="flex items-center gap-1 rounded-md bg-red-50 px-2 py-1 text-[11px] font-semibold text-red-600 transition-colors hover:bg-red-100">
                          <XCircle className="h-3 w-3" /> Reject
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Governance alerts */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2 pb-3">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <CardTitle className="text-sm font-semibold text-slate-800">AI Governance Alerts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {governanceAlerts.map(a => (
            <div key={a.msg} className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm ${
              a.severity === 'warn' ? 'bg-amber-50 text-amber-800' : 'bg-blue-50 text-blue-800'
            }`}>
              {a.severity === 'warn'
                ? <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                : <CheckCircle className="h-4 w-4 shrink-0 text-blue-500" />
              }
              {a.msg}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
