/** Onboarding Chat Page — dual-pane conversational AI assistant and onboarding task checklist. */
import { useState, useEffect, useRef } from 'react';
import {
  useSendMessageMutation,
  useGetTasksQuery,
  useCreateTaskMutation,
  useUpdateTaskMutation,
  useCompleteTaskMutation,
  useDeleteTaskMutation,
  useGetOverviewQuery,
} from '../api/onboardingApi';
import { ChatMessage } from '../components/ChatMessage';
import { TaskList } from '../components/TaskList';
import { TaskFormModal } from '../components/TaskFormModal';
import {
  Send,
  Plus,
  Sparkles,
  Loader2,
  Bot,
  ListTodo,
  FileText,
  X,
  RotateCcw,
  TrendingUp,
} from 'lucide-react';
import { useAppSelector } from '@/app/hooks';
import type { Task, CreateTaskRequest, UpdateTaskRequest, Citation, ChatMessage as ChatMessageType } from '../types';

export function OnboardingChatPage() {
  const user = useAppSelector((state) => state.auth.user);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [sendMessage, { isLoading: isSending }] = useSendMessageMutation();
  const { data: tasksData, refetch: refetchTasks, isLoading: isTasksLoading } = useGetTasksQuery();
  const { data: overviewData, refetch: refetchOverview } = useGetOverviewQuery();
  const [createTask, { isLoading: isCreating }] = useCreateTaskMutation();
  const [updateTask] = useUpdateTaskMutation();
  const [completeTask] = useCompleteTaskMutation();
  const [deleteTask] = useDeleteTaskMutation();

  const tasks = tasksData?.tasks ?? [];
  const completedCount = overviewData?.completedTasks ?? tasks.filter((t) => t.status === 'completed').length;
  const progressPct = overviewData?.progressPercentage ?? (tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0);


  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  // Initial welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        {
          role: 'assistant',
          content: `### Welcome to your HR Onboarding Assistant! 👋

I'm your dedicated AI onboarding guide. I can help you with:
- **HR & Benefits**: Healthcare enrollment, 401(k), paid time off, and probation period.
- **IT & Security**: Laptop provisioning, 1Password, VPN setup, and MFA.
- **Company Policies**: Code of conduct, expense reimbursement, and work-from-home guidelines.
- **Onboarding Tasks**: Track your checklist, mark items complete, or ask me to schedule new tasks.

Try asking one of the suggested questions below, or tell me: *"What are my remaining onboarding tasks?"*`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  }, []);

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || isSending) return;

    const userMessage: ChatMessageType = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const response = await sendMessage({
        question: text,
        conversation_id: conversationId ?? undefined,
        user_id: user?.id,
      }).unwrap();

      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          timestamp: new Date().toISOString(),
        },
      ]);

      // Automatically refresh tasks and overview
      refetchTasks();
      refetchOverview();
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'I encountered an error connecting to the onboarding assistant. Please try again.',
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
      refetchOverview();
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setShowTaskModal(true);
  };

  const handleUpdateTask = async (data: UpdateTaskRequest) => {
    if (!editingTask) return;
    try {
      await updateTask({ taskId: editingTask.task_id, data }).unwrap();
      setShowTaskModal(false);
      setEditingTask(null);
      refetchTasks();
      refetchOverview();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    const task = tasks.find((t) => t.task_id === taskId);
    if (!task) return;
    try {
      if (task.status === 'completed') {
        await updateTask({ taskId, data: { status: 'pending' as any } }).unwrap();
      } else {
        await completeTask(taskId).unwrap();
      }
      refetchTasks();
      refetchOverview();
    } catch (error) {
      console.error('Failed to toggle task completion:', error);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await deleteTask(taskId).unwrap();
      refetchTasks();
      refetchOverview();
    } catch (error) {
      console.error('Failed to delete task:', error);
    }
  };

  const handleTaskSubmit = async (data: CreateTaskRequest | UpdateTaskRequest) => {
    if (editingTask) {
      await handleUpdateTask(data as UpdateTaskRequest);
    } else {
      await handleCreateTask(data as CreateTaskRequest);
    }
  };

  const handleResetChat = () => {
    setConversationId(null);
    setMessages([
      {
        role: 'assistant',
        content: 'Conversation reset. How can I assist you with your onboarding today?',
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  const suggestedQuestions = [
    'How do I enroll in healthcare benefits?',
    'What is the standard probation period?',
    'What are the steps for Day 1 IT setup?',
    'Show my onboarding tasks',
    'Add a task for benefits enrollment by Friday',
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-slate-50/50">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-slate-200/80 shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-teal-800 flex items-center justify-center text-white shadow-xs">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900">HR Onboarding AI Employee</h1>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Grounded & Active
              </span>
            </div>
            <p className="text-xs text-slate-500">Autonomous multi-turn assistant for FAQ Q&A and task tracking</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleResetChat}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/70 rounded-lg transition-colors"
            title="Reset Conversation"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>New Chat</span>
          </button>
          <button
            onClick={() => {
              setEditingTask(null);
              setShowTaskModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-lg shadow-xs transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Add Task</span>
          </button>
        </div>
      </div>

      {/* Main Dual-Pane Hub */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden">
        {/* Left Pane: Conversational Assistant (7 cols) */}
        <div className="lg:col-span-7 flex flex-col h-full bg-slate-50/50 border-r border-slate-200/80 overflow-hidden">
          {/* Message Stream */}
          <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-4">
            {messages.map((message, index) => (
              <ChatMessage
                key={index}
                message={message}
                onCitationClick={(c) => setActiveCitation(c)}
              />
            ))}

            {isSending && (
              <div className="flex gap-3 items-center text-xs text-slate-500 animate-fade-in pl-2">
                <Loader2 className="h-4 w-4 animate-spin text-teal-600" />
                <span>Searching knowledge base & drafting response...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Bar */}
          <div className="px-4 md:px-6 py-2 bg-white/80 border-t border-slate-200/60 overflow-x-auto">
            <div className="flex items-center gap-1.5 whitespace-nowrap">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1 mr-1">
                <Sparkles className="h-3 w-3 text-amber-500" /> Suggested:
              </span>
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(q)}
                  className="text-xs bg-slate-100 hover:bg-teal-50 hover:text-teal-800 hover:border-teal-300 text-slate-700 px-2.5 py-1 rounded-full border border-slate-200 transition-all cursor-pointer"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Chat Input Box */}
          <div className="p-4 bg-white border-t border-slate-200/80">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-end gap-2 bg-slate-50 border border-slate-300/80 focus-within:border-teal-600 focus-within:ring-2 focus-within:ring-teal-600/20 rounded-2xl p-2 transition-all"
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask about onboarding policies, or say 'Create a task for...'"
                className="flex-1 bg-transparent border-0 focus:outline-none focus:ring-0 resize-none text-sm text-slate-800 placeholder-slate-400 min-h-[40px] max-h-28 px-2 py-1.5"
                rows={1}
                disabled={isSending}
              />
              <button
                type="submit"
                disabled={!input.trim() || isSending}
                className="w-9 h-9 rounded-xl bg-teal-700 hover:bg-teal-800 disabled:opacity-40 disabled:hover:bg-teal-700 text-white flex items-center justify-center transition-colors shadow-xs flex-shrink-0"
                aria-label="Send message"
              >
                {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </form>
            <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1.5 px-2">
              <span>Press <b>Enter</b> to send, <b>Shift + Enter</b> for new line</span>
              <span>Grounded in HR Knowledge Base</span>
            </div>
          </div>
        </div>

        {/* Right Pane: Interactive Onboarding Task Hub (5 cols) */}
        <div className="lg:col-span-5 flex flex-col h-full bg-white overflow-hidden">
          {/* Hub Header & Progress Card */}
          <div className="p-4 md:p-5 border-b border-slate-200/80 space-y-3 bg-gradient-to-b from-teal-50/40 to-transparent">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ListTodo className="h-5 w-5 text-teal-700" />
                <h2 className="text-sm font-bold text-slate-900">Onboarding Checklist</h2>
              </div>
              <span className="text-xs font-semibold text-teal-800 bg-teal-100/80 px-2 py-0.5 rounded-full">
                {completedCount} of {tasks.length} Done
              </span>
            </div>

            {/* Visual Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-600 font-medium">
                <span className="flex items-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5 text-teal-600" /> Journey Progress
                </span>
                <span className="font-bold text-slate-900">{progressPct}%</span>
              </div>
              <div className="w-full h-2.5 bg-slate-200/80 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-teal-600 to-teal-500 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          </div>

          {/* Task List Component */}
          <div className="flex-1 overflow-y-auto p-4 md:p-5">
            <TaskList
              tasks={tasks}
              onComplete={handleCompleteTask}
              onDelete={handleDeleteTask}
              onEdit={handleEditTask}
              loading={isTasksLoading}
            />
          </div>

          {/* Footer Guide Note */}
          <div className="p-3 bg-slate-50 border-t border-slate-200/80 text-[11px] text-slate-500 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-teal-600 flex-shrink-0" />
            <span>You can ask the AI anytime: <i>"Mark I-9 verification as done"</i></span>
          </div>
        </div>
      </div>

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

      {/* Citation Inspector Modal */}
      {activeCitation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[85vh] overflow-hidden border border-slate-200 flex flex-col animate-scale-in">
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50/70">
              <div className="flex items-center gap-2 text-slate-900 font-semibold text-sm">
                <FileText className="h-4 w-4 text-teal-600" />
                <span>Source Document Citation</span>
              </div>
              <button
                onClick={() => setActiveCitation(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-3">
              <div className="bg-teal-50/50 border border-teal-200/70 rounded-xl p-3 text-xs space-y-1">
                <div className="font-semibold text-teal-900 flex items-center justify-between">
                  <span>📄 {activeCitation.filename || 'HR Policy Document'}</span>
                  {activeCitation.score && (
                    <span className="text-[10px] bg-teal-100 text-teal-800 px-1.5 py-0.5 rounded-full font-mono">
                      Score: {Math.round(activeCitation.score * 100)}%
                    </span>
                  )}
                </div>
                {activeCitation.section && (
                  <p className="text-teal-700">Section / Topic: <b>{activeCitation.section}</b></p>
                )}
              </div>

              <div>
                <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Extracted Grounding Passage:
                </h4>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs text-slate-800 font-mono leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap">
                  {activeCitation.content || 'Content excerpt loaded from Chroma vector store.'}
                </div>
              </div>
            </div>

            <div className="p-3 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => setActiveCitation(null)}
                className="px-4 py-1.5 bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

