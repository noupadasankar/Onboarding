/** Onboarding API client using RTK Query. */
import { baseApi } from '@/app/api/baseApi';
import type {
  Task,
  TaskListResponse,
  CreateTaskRequest,
  UpdateTaskRequest,
  OnboardingChatRequest,
  OnboardingChatResponse,
} from '../types';

export const onboardingApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // Chat endpoint
    sendMessage: builder.mutation<OnboardingChatResponse, OnboardingChatRequest>({
      query: (body) => ({
        url: '/onboarding/chat',
        method: 'POST',
        body,
      }),
    }),

    // Task endpoints
    getTasks: builder.query<TaskListResponse, void>({
      query: () => '/onboarding/tasks',
      providesTags: ['Task'],
    }),

    createTask: builder.mutation<Task, CreateTaskRequest>({
      query: (body) => ({
        url: '/onboarding/tasks',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Task'],
    }),

    getTask: builder.query<Task, string>({
      query: (taskId) => `/onboarding/tasks/${taskId}`,
      providesTags: (_, __, id) => [{ type: 'Task', id }],
    }),

    updateTask: builder.mutation<Task, { taskId: string; data: UpdateTaskRequest }>({
      query: ({ taskId, data }) => ({
        url: `/onboarding/tasks/${taskId}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: (_, __, { taskId }) => [{ type: 'Task', id: taskId }],
    }),

    completeTask: builder.mutation<Task, string>({
      query: (taskId) => ({
        url: `/onboarding/tasks/${taskId}/complete`,
        method: 'PATCH',
      }),
      invalidatesTags: (_, __, taskId) => [{ type: 'Task', id: taskId }],
    }),

    deleteTask: builder.mutation<void, string>({
      query: (taskId) => ({
        url: `/onboarding/tasks/${taskId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Task'],
    }),
  }),
});

export const {
  useSendMessageMutation,
  useGetTasksQuery,
  useCreateTaskMutation,
  useGetTaskQuery,
  useUpdateTaskMutation,
  useCompleteTaskMutation,
  useDeleteTaskMutation,
} = onboardingApi;
