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
import { DollarSign, FileText, TrendingUp, ShieldAlert } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const deptSpending = [
  { dept: 'Engineering', amount: 620 },
  { dept: 'Sales', amount: 480 },
  { dept: 'Operations', amount: 390 },
  { dept: 'HR', amount: 210 },
  { dept: 'Finance', amount: 175 },
];

const monthlyExpenses = [
  { month: 'Jan', amount: 185 },
  { month: 'Feb', amount: 210 },
  { month: 'Mar', amount: 198 },
  { month: 'Apr', amount: 225 },
  { month: 'May', amount: 240 },
  { month: 'Jun', amount: 218 },
  { month: 'Jul', amount: 195 },
];

const transactions = [
  { vendor: 'AWS Cloud Services', dept: 'Engineering', amount: '$12,450', date: 'Jul 10', flag: false },
  { vendor: 'Office Depot', dept: 'Operations', amount: '$3,200', date: 'Jul 9', flag: false },
  { vendor: 'Unknown Vendor X', dept: 'Finance', amount: '$45,000', date: 'Jul 9', flag: true },
  { vendor: 'LinkedIn Talent', dept: 'HR', amount: '$8,100', date: 'Jul 8', flag: false },
  { vendor: 'Salesforce CRM', dept: 'Sales', amount: '$21,600', date: 'Jul 7', flag: false },
];

export function FinanceDashboard() {
  const budgetUsedPct = 68;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Finance Dashboard</h1>
        <p className="text-sm text-slate-500">Budget management & expense analytics · July 2026</p>
      </div>

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Total Budget</CardTitle>
            <DollarSign className="h-4 w-4 text-teal-600" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">$2.4M</p>
            <p className="mt-1 text-xs text-slate-400">FY 2026 allocation</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Budget Used</CardTitle>
            <TrendingUp className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{budgetUsedPct}%</p>
            <div className="mt-2 h-1.5 w-full rounded-full bg-slate-200">
              <div
                className="h-1.5 rounded-full bg-amber-500"
                style={{ width: `${budgetUsedPct}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Pending Invoices</CardTitle>
            <FileText className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">23</p>
            <p className="mt-1 text-xs text-slate-400">$128k value</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium uppercase tracking-wide text-slate-500">Fraud Alerts</CardTitle>
            <ShieldAlert className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">2</p>
            <p className="mt-1 text-xs text-red-400 font-medium">Requires review</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Dept spending bar chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Spend by Department (K$)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={deptSpending} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="dept" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(v) => `$${Number(v)}K`}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                />
                <Bar dataKey="amount" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Spend (K$)" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Monthly expenses line chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-slate-800">Monthly Expenses (K$)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={monthlyExpenses} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} domain={[150, 260]} />
                <Tooltip
                  formatter={(v) => `$${Number(v)}K`}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                />
                <Line type="monotone" dataKey="amount" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4, fill: '#f59e0b' }} name="Expenses (K$)" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Transactions table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold text-slate-800">Recent Transactions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Vendor</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Department</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Amount</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Date</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-slate-500">Flag</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {transactions.map(t => (
                <tr key={t.vendor + t.date} className={t.flag ? 'bg-red-50' : 'hover:bg-slate-50'}>
                  <td className="px-4 py-3 font-medium text-slate-800">{t.vendor}</td>
                  <td className="px-4 py-3 text-slate-600">{t.dept}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">{t.amount}</td>
                  <td className="px-4 py-3 text-slate-500">{t.date}</td>
                  <td className="px-4 py-3">
                    {t.flag && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                        <ShieldAlert className="h-3 w-3" /> Fraud Alert
                      </span>
                    )}
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
