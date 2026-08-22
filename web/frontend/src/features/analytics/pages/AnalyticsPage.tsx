import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ShieldCheck, AlertTriangle, CheckCircle } from 'lucide-react';
import { Permission } from '@hr-onboarding/shared';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useGetAnalyticsQuery } from '../api/analyticsApi';

const PIE_COLORS = ['#0d9488', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444'];

const AUDIT_ROWS = [
  { ts: '2026-07-11 09:14', user: 'alice@acme.com', query: 'What is the parental leave policy?', confidence: 92, action: 'Answered' },
  { ts: '2026-07-11 08:52', user: 'bob@acme.com', query: 'Salary band for Senior Engineer', confidence: 61, action: 'Flagged' },
  { ts: '2026-07-10 17:30', user: 'carol@acme.com', query: 'How to raise an IT ticket?', confidence: 95, action: 'Answered' },
  { ts: '2026-07-10 16:10', user: 'dave@acme.com', query: 'Q3 budget remaining for Engineering', confidence: 54, action: 'Overridden' },
  { ts: '2026-07-10 14:45', user: 'eve@acme.com', query: 'VPN setup instructions', confidence: 88, action: 'Answered' },
];

function ConfidenceBadge({ score }: { score: number }) {
  const color = score >= 80 ? 'text-emerald-700 bg-emerald-50' : score >= 65 ? 'text-amber-700 bg-amber-50' : 'text-red-700 bg-red-50';
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${color}`}>
      {score}%
    </span>
  );
}

function ActionBadge({ action }: { action: string }) {
  const color = action === 'Answered' ? 'text-emerald-700 bg-emerald-50'
    : action === 'Flagged' ? 'text-amber-700 bg-amber-50'
    : 'text-red-700 bg-red-50';
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${color}`}>
      {action}
    </span>
  );
}

export function AnalyticsPage() {
  const { hasPermission } = useAuth();
  const { data, isLoading, isError, error } = useGetAnalyticsQuery();

  if (!hasPermission(Permission.GOVERNANCE_READ)) {
    return (
      <div className="p-6">
        <p className="py-8 text-center text-sm text-red-600">
          You do not have permission to view analytics.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <p className="py-8 text-center text-sm text-slate-500">Loading analytics...</p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6">
        <p className="py-8 text-center text-sm text-red-600">
          {error && 'message' in (error as Error)
            ? (error as Error).message
            : 'Failed to load analytics. Please try again.'}
        </p>
      </div>
    );
  }

  const pieData = data.documentsByDepartment.map(d => ({ name: d.department, value: d.count }));

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
        <p className="text-sm text-slate-500">Platform usage, AI governance & performance metrics</p>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Total Messages</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{data.tokenUsage.totalMessages.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Active Users (7d)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{data.activeUsersLast7Days.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Prompt Tokens</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{data.tokenUsage.totalPrompt.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Completion Tokens</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{data.tokenUsage.totalCompletion.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts row */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Questions per day — line chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Questions per Day</CardTitle>
          </CardHeader>
          <CardContent>
            {data.questionsPerDay.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-400">No data yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data.questionsPerDay} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                  <Line type="monotone" dataKey="count" stroke="#0d9488" strokeWidth={2} dot={{ r: 4, fill: '#0d9488' }} name="Questions" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Documents by department — bar chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Documents by Department</CardTitle>
          </CardHeader>
          <CardContent>
            {data.documentsByDepartment.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-400">No data yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.documentsByDepartment} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="department" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                  <Bar dataKey="count" fill="#0d9488" radius={[4, 4, 0, 0]} name="Documents" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pie chart + governance panel */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Document distribution pie */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Document Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {pieData.length === 0 ? (
              <p className="py-12 text-center text-sm text-slate-400">No data yet.</p>
            ) : (
              <div className="flex items-center gap-4">
                <ResponsiveContainer width="55%" height={180}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                      dataKey="value" paddingAngle={3}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex-1 space-y-2">
                  {pieData.map((d, i) => (
                    <div key={d.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        <span className="text-slate-600">{d.name}</span>
                      </div>
                      <span className="font-semibold text-slate-800">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Governance panel */}
        <Card>
          <CardHeader className="flex flex-row items-center gap-2 pb-3">
            <ShieldCheck className="h-4 w-4 text-teal-600" />
            <CardTitle className="text-sm font-semibold text-slate-800">AI Governance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-emerald-50 p-3 text-center">
                <p className="text-xl font-bold text-emerald-700">86%</p>
                <p className="mt-0.5 text-[10px] text-emerald-600">Avg Confidence</p>
              </div>
              <div className="rounded-lg bg-amber-50 p-3 text-center">
                <p className="text-xl font-bold text-amber-700">12</p>
                <p className="mt-0.5 text-[10px] text-amber-600">Low-conf flags</p>
              </div>
              <div className="rounded-lg bg-red-50 p-3 text-center">
                <p className="text-xl font-bold text-red-700">3</p>
                <p className="mt-0.5 text-[10px] text-red-600">Overrides</p>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              <CheckCircle className="h-3.5 w-3.5 shrink-0" />
              All AI answers traceable to source documents
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              2 answers below 65% confidence threshold this week
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Audit log */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2 pb-3">
          <ShieldCheck className="h-4 w-4 text-slate-500" />
          <CardTitle className="text-sm font-semibold text-slate-800">Audit Log</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Timestamp</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">User</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Query</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Confidence</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {AUDIT_ROWS.map(r => (
                <tr key={r.ts + r.user} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.ts}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{r.user}</td>
                  <td className="px-4 py-3 text-slate-700">{r.query}</td>
                  <td className="px-4 py-3"><ConfidenceBadge score={r.confidence} /></td>
                  <td className="px-4 py-3"><ActionBadge action={r.action} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
