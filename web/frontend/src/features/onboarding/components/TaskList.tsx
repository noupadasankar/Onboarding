/** Task list component for onboarding tasks with category filters and interactive actions. */
import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { Task, TaskPriority } from '../types';
import {
  CheckCircle2,
  Circle,
  Calendar,
  Trash2,
  Edit3,
  ShieldCheck,
  Laptop,
  DollarSign,
  Users,
  Layers,
} from 'lucide-react';

interface TaskListProps {
  tasks: Task[];
  onComplete: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onEdit?: (task: Task) => void;
  loading?: boolean;
}

const categoryIcons: Record<string, typeof Users> = {
  HR: Users,
  IT: Laptop,
  Finance: DollarSign,
  Compliance: ShieldCheck,
  General: Layers,
};

const categoryBadgeColors: Record<string, string> = {
  HR: 'text-teal-700 bg-teal-50 border-teal-200',
  IT: 'text-blue-700 bg-blue-50 border-blue-200',
  Finance: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  Compliance: 'text-purple-700 bg-purple-50 border-purple-200',
  General: 'text-slate-700 bg-slate-50 border-slate-200',
};

const priorityConfig: Record<TaskPriority, { label: string; color: string }> = {
  low: { label: 'Low', color: 'text-slate-500 bg-slate-100' },
  medium: { label: 'Medium', color: 'text-amber-700 bg-amber-50 border border-amber-200' },
  high: { label: 'High', color: 'text-rose-700 bg-rose-50 border border-rose-200' },
};

export function TaskList({ tasks, onComplete, onDelete, onEdit, loading }: TaskListProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="animate-pulse bg-slate-100/80 rounded-xl p-3.5 h-20" />
        ))}
      </div>
    );
  }

  const categories = ['all', 'HR', 'IT', 'Finance', 'Compliance'];
  const filteredTasks = selectedCategory === 'all'
    ? tasks
    : tasks.filter((t) => (t.category || 'HR').toLowerCase() === selectedCategory.toLowerCase());

  return (
    <div className="space-y-3">
      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
        {categories.map((cat) => {
          const count = cat === 'all'
            ? tasks.length
            : tasks.filter((t) => (t.category || 'HR').toLowerCase() === cat.toLowerCase()).length;
          const isActive = selectedCategory === cat;
          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={cn(
                'px-2.5 py-1 rounded-lg font-medium whitespace-nowrap transition-colors flex items-center gap-1',
                isActive
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200/70'
              )}
            >
              <span>{cat === 'all' ? 'All Tasks' : cat}</span>
              <span className={cn('text-[10px] px-1 rounded-full', isActive ? 'bg-teal-800 text-teal-100' : 'bg-slate-200 text-slate-600')}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredTasks.length === 0 && (
        <div className="text-center py-8 px-4 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
          <CheckCircle2 className="mx-auto h-8 w-8 text-teal-500/40 mb-2" />
          <p className="text-sm font-medium text-slate-700">No tasks in this category</p>
          <p className="text-xs text-slate-500 mt-0.5">Tell the AI to create an onboarding task for you anytime!</p>
        </div>
      )}

      {/* Task Cards */}
      <div className="space-y-2">
        {filteredTasks.map((task) => {
          const isCompleted = task.status === 'completed';
          const cat = task.category || 'HR';
          const CatIcon = categoryIcons[cat] || Layers;
          const prio = priorityConfig[task.priority] || priorityConfig.medium;

          return (
            <div
              key={task.task_id}
              className={cn(
                'group relative rounded-xl border p-3 transition-all',
                isCompleted
                  ? 'bg-slate-50/60 border-slate-200 opacity-75'
                  : 'bg-white border-slate-200/90 hover:border-teal-300 hover:shadow-xs'
              )}
            >
              <div className="flex items-start gap-2.5">
                {/* Complete checkbox */}
                <button
                  onClick={() => onComplete(task.task_id)}
                  className="mt-0.5 flex-shrink-0 text-slate-400 hover:text-teal-600 transition-colors"
                  title={isCompleted ? 'Mark pending' : 'Mark complete'}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-5 w-5 text-teal-600 fill-teal-50" />
                  ) : (
                    <Circle className="h-5 w-5 hover:stroke-teal-600" />
                  )}
                </button>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-1">
                    <h4
                      className={cn(
                        'text-xs font-semibold text-slate-900 leading-snug',
                        isCompleted && 'line-through text-slate-400 font-normal'
                      )}
                    >
                      {task.title}
                    </h4>

                    {/* Quick action buttons on hover */}
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      {onEdit && (
                        <button
                          onClick={() => onEdit(task)}
                          className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                          title="Edit Task"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                      )}
                      <button
                        onClick={() => onDelete(task.task_id)}
                        className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                        title="Delete Task"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {task.description && (
                    <p className={cn('text-[11px] text-slate-500 mt-1 line-clamp-2', isCompleted && 'text-slate-400')}>
                      {task.description}
                    </p>
                  )}

                  {/* Badges footer */}
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    {/* Category */}
                    <span className={cn('inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium border', categoryBadgeColors[cat] || categoryBadgeColors.General)}>
                      <CatIcon className="h-2.5 w-2.5" />
                      {cat}
                    </span>

                    {/* Priority */}
                    <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium', prio.color)}>
                      {prio.label}
                    </span>

                    {/* Due Date */}
                    {task.due_date && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 ml-auto">
                        <Calendar className="h-2.5 w-2.5 text-slate-400" />
                        {task.due_date}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

