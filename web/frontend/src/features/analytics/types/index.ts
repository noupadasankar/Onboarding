export interface AnalyticsData {
  questionsPerDay: Array<{ date: string; count: number }>;
  documentsByDepartment: Array<{ department: string; count: number }>;
  tokenUsage: { totalPrompt: number; totalCompletion: number; totalMessages: number };
  activeUsersLast7Days: number;
}
