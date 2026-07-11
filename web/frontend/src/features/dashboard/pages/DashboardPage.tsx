import { useAuth } from '@/features/auth/hooks/useAuth';
import { EmployeeDashboard } from '../components/EmployeeDashboard';
import { HRDashboard } from '../components/HRDashboard';
import { FinanceDashboard } from '../components/FinanceDashboard';
import { ITDashboard } from '../components/ITDashboard';

export function DashboardPage() {
  const { user } = useAuth();

  switch (user?.role) {
    case 'HR_MANAGER':
      return <HRDashboard />;
    case 'FINANCE_ADMIN':
      return <FinanceDashboard />;
    case 'IT_ADMIN':
      return <ITDashboard />;
    default:
      return <EmployeeDashboard email={user?.email ?? ''} />;
  }
}
