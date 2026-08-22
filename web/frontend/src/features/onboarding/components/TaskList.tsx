/** Task list component for onboarding tasks. */
import { cn } from '@/lib/utils';
import type { Task, TaskStatus, TaskPriority } from '../types';
import {
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  Flag,
  Calendar,
  Trash2,
  Edit,
} from 'lucide-react';

interface TaskListProps {
  tasks: Task[];
  onComplete: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onEdit?: (task: Task) => void;
  loading?: boolean;
}

const statusConfig: Record<TaskStatus, { icon: typeof CheckCircle; label: string; color: string }> = {
  pending: { icon: Clock, label: 'Pending', color: 'text-yellow-600 bg-yellow-100' },
  in_progress: { icon: AlertCircle, label: 'In Progress', color: 'text-blue-600 bg-blue-100' },
  completed: { icon: CheckCircle, label: 'Completed', color: 'text-green-600 bg-green-100' },
  cancelled: { icon: XCircle, label: 'Cancelled', color: 'text-gray-600 bg-gray-100' },
};

const priorityConfig: Record<TaskPriority, { icon: typeof Flag; color: string }> = {
  low: { icon: Flag, color: 'text-gray-500' },
  medium: { icon: Flag, color: 'text-orange-500' },
  high: { icon: Flag, color: 'text-red-500' },
};

export function TaskList({ tasks, onComplete, onDelete, onEdit, loading }: TaskListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-muted rounded w-3/4 mb-2" />
            <div className="h-3 bg-muted rounded w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <CheckCircle className="mx-auto h-12 w-12 opacity-30 mb-3" />
        <p className="text-sm">No onboarding tasks yet</p>
        <p className="text-xs mt-1">Ask the AI to create tasks for you!</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {tasks.map((task) => {
        const status = statusConfig[task.status];
        const priority = priorityConfig[task.priority];
        const StatusIcon = status.icon;
        const PriorityIcon = priority.icon;
        const isCompleted = task.status === 'completed';

        return (
          <div
            key={task.task_id}
            className={cn(
              'border rounded-lg p-4 transition-all',
              isCompleted ? 'opacity-60 bg-green-50' : 'bg-card'
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className={cn('font-medium text-sm', isCompleted && 'line-through')}>
                    {task.title}
                  </h4>
                  <span
                    className={cn(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      status.color
                    )}
                  >
                    <StatusIcon className="h-3 w-3 mr-1" />
                    {status.label}
                  </span>
                  <span
                    className={cn(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      priority.color
                    )}
                  >
                    <PriorityIcon className="h-3 w-3 mr-1" />
                    {task.priority}
                  </span>
                </div>
                {task.description && (
                  <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                    {task.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  {task.due_date && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      Due: {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Created: {new Date(task.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {!isCompleted && (
                  <button
                    onClick={() => onComplete(task.task_id)}
                    className="p-1.5 rounded hover:bg-green-100 text-green-600 transition-colors"
                    title="Mark complete"
                  >
                    <CheckCircle className="h-4 w-4" />
                  </button>
                )}
                {onEdit && (
                  <button
                    onClick={() => onEdit(task)}
                    className="p-1.5 rounded hover:bg-blue-100 text-blue-600 transition-colors"
                    title="Edit"
                  >
                    <Edit className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={() => onDelete(task.task_id)}
                  className="p-1.5 rounded hover:bg-red-100 text-red-600 transition-colors"
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
