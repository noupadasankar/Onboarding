import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LoginForm } from '../components/LoginForm';
import { DEMO_CREDENTIALS, DEMO_PASSWORD } from '../constants';

export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>OptiAgent</CardTitle>
          <CardDescription>Sign in to the enterprise AI operations platform</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <LoginForm />
          <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-500">
            <p className="mb-1 font-medium text-slate-600">Demo accounts (password: {DEMO_PASSWORD})</p>
            <ul className="space-y-0.5">
              {DEMO_CREDENTIALS.map((c) => (
                <li key={c.email}>
                  <span className="font-medium">{c.label}:</span> {c.email}
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
