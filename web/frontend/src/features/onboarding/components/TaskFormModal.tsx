/** Task form modal for creating/editing tasks. */
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { X, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { Task, CreateTaskRequest, UpdateTaskRequest, TaskPriority } from '../types';
import { z } from 'zod';

const taskSchema = z.object({
  title: z.string().min(1, 'Title is required').max(200),
  description: z.string().optional(),
  due_date: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']).default('medium'),
});

type TaskFormData = z.infer<typeof taskSchema>;

interface TaskFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CreateTaskRequest | UpdateTaskRequest) => void;
  initialData?: Task;
  isEditing?: boolean;
  loading?: boolean;
}

export function TaskFormModal({ open, onClose, onSubmit, initialData, isEditing, loading }: TaskFormModalProps) {
  const form = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: '',
      description: '',
      due_date: '',
      priority: 'medium',
    },
  });

  useEffect(() => {
    if (open && initialData) {
      form.reset({
        title: initialData.title,
        description: initialData.description ?? '',
        due_date: initialData.due_date ? initialData.due_date.split('T')[0] : '',
        priority: initialData.priority,
      });
    } else if (open) {
      form.reset({
        title: '',
        description: '',
        due_date: '',
        priority: 'medium',
      });
    }
  }, [open, initialData, form]);

  const handleSubmit = (data: TaskFormData) => {
    const submitData: CreateTaskRequest | UpdateTaskRequest = {
      title: data.title,
      description: data.description || undefined,
      due_date: data.due_date || undefined,
      priority: data.priority as TaskPriority,
    };
    onSubmit(submitData);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-card rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            {isEditing ? 'Edit Task' : 'Create Onboarding Task'}
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-muted transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={form.handleSubmit(handleSubmit)} className="p-4 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="title">Task Title *</Label>
            <Input
              id="title"
              {...form.register('title')}
              placeholder="e.g., Complete benefits enrollment"
              disabled={loading}
            />
            {form.formState.errors.title && (
              <p className="text-sm text-red-500">{form.formState.errors.title.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...form.register('description')}
              placeholder="Add details about this task..."
              rows={3}
              disabled={loading}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="due_date">Due Date</Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="due_date"
                  type="date"
                  {...form.register('due_date')}
                  className="pl-10"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="priority">Priority</Label>
              <Select
                value={form.watch('priority') as TaskPriority}
                onValueChange={(v) => form.setValue('priority', v as TaskPriority)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Task'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
