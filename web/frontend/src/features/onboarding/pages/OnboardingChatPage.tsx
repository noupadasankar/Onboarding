/** Onboarding Chat Page — main conversational interface for new hires. */
import { useState, useEffect, useRef } from 'react';
import { useSendMessageMutation, useGetTasksQuery, useCreateTaskMutation } from '../api/onboardingApi';
import { ChatMessage } from '../components/ChatMessage';
import { TaskList } from '../components/TaskList';
import { TaskFormModal } from '../components/TaskFormModal';
import { Send, Plus, Sparkles, Loader2, Bot } from 'lucide-react';
import { useAppSelector } from '@/app/hooks';
import { cn } from '@/lib/utils';
import type { TaskPriority, TaskStatus, CreateTaskRequest, UpdateTaskRequest } from '../types';

export function OnboardingChatPage() {
  const user = useAppSelector((state) => state.auth.user);
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; timestamp?: string }>>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [editingTask, setEditingTask] = useState<null | { task_id: string; user_id: string; title: string; description: string; status: TaskStatus; priority: TaskPriority; due_date: string | null; created_at: string; updated_at: string; completed_at: string | null }>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [sendMessage, { isLoading: isSending }] = useSendMessageMutation();
  const { data: tasksData, refetch: refetchTasks } = useGetTasksQuery();
  const [createTask, { isLoading: isCreating }] = useCreateTaskMutation();

  const tasks = tasksData?.tasks ?? [];

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initial welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          role: 'assistant',
          content: `Welcome to your HR Onboarding Assistant! 👋

I'm here to help you navigate your onboarding journey. You can ask me questions about:
- Company policies and procedures
- Benefits and leave policies
- IT setup and equipment
- Your 30/60/90-day plan
- And much more!

I can also help you create and track onboarding tasks. Just ask me things like:
- "Create a task for me to complete benefits enrollment by Friday"
- "What tasks do I have pending?"
- "Mark my laptop setup task as complete"

How can I help you today?`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  }, []);

  const handleSendMessage = async (e: React.FormEvent<HTMLFormElement> | React.KeyboardEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    if (!input.trim() || !user || isSending) return;

    const userMessage = { role: 'user' as const, content: input, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput('');

    try {
      const response = await sendMessage({
        question: currentInput,
        conversation_id: conversationId ?? undefined,
        user_id: user.id,
      }).unwrap();

      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          timestamp: new Date().toISOString(),
        },
      ]);

      // Refetch tasks if they might have been updated
      if (response.tasks_updated) {
        refetchTasks();
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const handleCreateTask = async (data: CreateTaskRequest) => {
    try {
      await createTask(data).unwrap();
      setShowTaskModal(false);
      refetchTasks();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleEditTask = (task: typeof tasks[0]) => {
    setEditingTask({
      task_id: task.task_id,
      user_id: task.user_id,
      title: task.title,
      description: task.description,
      status: task.status,
      priority: task.priority,
      due_date: task.due_date,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    });
    setShowTaskModal(true);
  };

  const handleUpdateTask = async (data: UpdateTaskRequest) => {
    // We'll use the create task mutation for updates too (simplified)
    try {
      await createTask(data as CreateTaskRequest).unwrap();
      setShowTaskModal(false);
      setEditingTask(null);
      refetchTasks();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleCompleteTask = async (_taskId: string) => {
    // This would need a complete task mutation
    refetchTasks();
  };

  const handleDeleteTask = async (_taskId: string) => {
    // This would need a delete task mutation
    refetchTasks();
  };

  const handleTaskSubmit = async (data: CreateTaskRequest | UpdateTaskRequest) => {
    if (editingTask) {
      await handleUpdateTask(data as UpdateTaskRequest);
    } else {
      await handleCreateTask(data as CreateTaskRequest);
    }
  };

  const suggestedQuestions = [
    "What's my 30-day plan?",
    "How do I enroll in benefits?",
    "What's the holiday schedule?",
    "Create a task for IT setup",
    "Show my tasks",
  ];

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-card">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Bot className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">HR Onboarding Assistant</h1>
            <p className="text-sm text-muted-foreground">Your personal onboarding guide</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTaskModal(true)}
            className={cn(
              'inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors',
              'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            <Plus className="h-4 w-4" />
            Create Task
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="max-w-3xl mx-auto w-full space-y-4">
          {messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions */}
        {messages.length <= 1 && (
          <div className="max-w-3xl mx-auto w-full">
            <p className="text-sm text-muted-foreground mb-3 text-center">Try asking:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestedQuestions.map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    // Trigger form submission
                    const form = document.querySelector('form');
                    form?.requestSubmit?.();
                  }}
                  className="px-3 py-1.5 text-sm rounded-lg border bg-card hover:bg-muted transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Task Panel */}
      <div className="border-t bg-card">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-medium flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Your Onboarding Tasks ({tasks.length})
          </h2>
        </div>
        <div className="p-4 max-h-60 overflow-y-auto">
          <TaskList
            tasks={tasks}
            onComplete={handleCompleteTask}
            onDelete={handleDeleteTask}
            onEdit={handleEditTask}
            loading={tasksData === undefined}
          />
        </div>
      </div>

      {/* Input Area */}
      <form onSubmit={handleSendMessage} className="p-4 border-t bg-card">
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder="Ask me anything about onboarding..."
              className={cn(
                'w-full min-h-[44px] max-h-32 px-4 py-3 pr-12 rounded-xl border bg-background',
                'focus:outline-none focus:ring-2 focus:ring-primary/50',
                'resize-none text-sm'
              )}
              disabled={isSending}
              rows={1}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isSending}
            className={cn(
              'p-2 rounded-xl transition-colors flex-shrink-0',
              'bg-primary text-primary-foreground hover:bg-primary/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            aria-label="Send message"
          >
            {isSending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>

      {/* Task Form Modal */}
      <TaskFormModal
        open={showTaskModal}
        onClose={() => {
          setShowTaskModal(false);
          setEditingTask(null);
        }}
        onSubmit={handleTaskSubmit}
        initialData={editingTask || undefined}
        isEditing={!!editingTask}
        loading={isCreating}
      />
    </div>
  );
}
