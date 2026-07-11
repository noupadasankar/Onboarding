import { useEffect, useRef, useState } from 'react';
import { ConversationSidebar } from '../components/ConversationSidebar';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';
import {
  useChatMutation,
  useGetConversationQuery,
  useListConversationsQuery,
} from '../api/chatApi';
import type { MessageDTO } from '../types';

const DEPARTMENTS = [
  { name: 'hr', displayName: 'Human Resources' },
  { name: 'finance', displayName: 'Finance' },
  { name: 'it', displayName: 'Information Technology' },
  { name: 'general', displayName: 'General' },
];

export function ChatPage() {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [optimisticMessages, setOptimisticMessages] = useState<MessageDTO[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: conversationList, isLoading: listLoading } = useListConversationsQuery({});

  const {
    data: conversationDetail,
    isFetching: convFetching,
    refetch: refetchConversation,
  } = useGetConversationQuery(activeConversationId!, {
    skip: activeConversationId == null,
  });

  const [chat, { isLoading: chatLoading }] = useChatMutation();

  const messages: MessageDTO[] = activeConversationId
    ? [...(conversationDetail?.messages ?? []), ...optimisticMessages]
    : optimisticMessages;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  // Clear optimistic messages once the conversation reloads and includes them
  useEffect(() => {
    if (conversationDetail && optimisticMessages.length > 0) {
      setOptimisticMessages([]);
    }
  }, [conversationDetail?.messages?.length]);

  function handleNew() {
    setActiveConversationId(null);
    setOptimisticMessages([]);
  }

  function handleSelect(id: string) {
    setActiveConversationId(id);
    setOptimisticMessages([]);
  }

  async function handleSend(question: string, departmentHint?: string) {
    // Add optimistic user message
    const optimisticUserMsg: MessageDTO = {
      id: `optimistic-${Date.now()}`,
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    };
    setOptimisticMessages((prev) => [...prev, optimisticUserMsg]);

    try {
      const result = await chat({
        question,
        conversationId: activeConversationId ?? undefined,
        departmentHint,
      }).unwrap();

      // Set active conversation if this was a new one
      if (activeConversationId == null) {
        setActiveConversationId(result.conversationId);
        setOptimisticMessages([]);
      } else {
        // Refetch to get the real messages including the assistant reply
        await refetchConversation();
        setOptimisticMessages([]);
      }
    } catch {
      // Remove optimistic message on failure
      setOptimisticMessages((prev) =>
        prev.filter((m) => m.id !== optimisticUserMsg.id),
      );
    }
  }

  const conversations = conversationList?.items ?? [];

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={handleSelect}
        onNew={handleNew}
        isLoading={listLoading}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {activeConversationId == null && optimisticMessages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-slate-400">Select a conversation or start a new one</p>
          </div>
        ) : convFetching && messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-slate-400">Loading…</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}

        <ChatInput
          onSend={handleSend}
          isLoading={chatLoading}
          departments={DEPARTMENTS}
        />
      </div>
    </div>
  );
}
