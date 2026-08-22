"""HR Onboarding Agent — handles onboarding Q&A and task management for new hires."""
from __future__ import annotations

import json
import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState
from app.retrieval.retrieval_service import RetrievalService, RetrievalConfig
from app.retrieval.retrieval_pipeline import RetrievalPipeline
from app.retrieval.prompt_builder import PromptBuilder
from app.tools.retrieval_tool import RetrievalTool
from app.tools.task_tool import TaskTool, TaskOperation

_log = get_logger()

ONBOARDING_SYSTEM_PROMPT = """You are the HR Onboarding AI Employee — a conversational agent that helps new hires navigate their onboarding journey.

Your role:
- Answer onboarding questions grounded ONLY in the provided HR documents (onboarding process, FAQs, policies, handbook)
- Create and track onboarding tasks for new hires
- Allow users to check task status conversationally
- Handle multi-turn conversations naturally (e.g., ask clarifying questions, remember context)

Rules:
- Answer ONLY from the provided context. Never invent or assume HR policies.
- If the answer is not found in the context, respond with: "I couldn't find that information in the uploaded HR documents."
- When quoting a policy, cite the source document and section.
- Keep answers concise, clear, and well-structured.
- Always use professional, warm, and welcoming language appropriate for new hires.
- For task creation: extract task details from the conversation and confirm with the user before creating.
- For task status: retrieve and present the current status of user's tasks.
- Maintain conversation context across turns — remember what the user has asked and what tasks they've created.

Available tools:
- retrieve_context: Search HR documents for relevant information
- manage_tasks: Create, update, list, or complete onboarding tasks

When the user wants to create a task, ask clarifying questions to get:
1. Task title (required)
2. Task description (optional)
3. Due date (optional)
4. Priority: low, medium, high (default: medium)

When the user asks about task status, use the manage_tasks tool with operation "list" to show their current tasks.
"""

TASK_CREATION_PROMPT = """The user wants to create an onboarding task. Extract the following from the conversation:
- title: Brief task title (required)
- description: Detailed description (optional)
- due_date: Due date in YYYY-MM-DD format (optional)
- priority: low, medium, or high (default: medium)

If any required information is missing, ask the user for it. Once you have all the information, confirm with the user before creating the task.
"""

TASK_STATUS_PROMPT = """The user wants to check their onboarding task status. Use the manage_tasks tool with operation "list" to retrieve their current tasks and present them in a clear, organized way."""


async def onboarding_agent_node(
    state: GraphState,
    retrieval_tool: RetrievalTool,
    llm_service: LLMService,
) -> dict[str, Any]:
    """Onboarding agent node for LangGraph."""
    question = state.get("question", "")
    user_id = state.get("user_id", "")
    conversation_id = state.get("conversation_id", "")
    messages = state.get("messages", [])
    
    settings = get_settings()
    vector_service = retrieval_tool.vector_service
    retrieval_svc = RetrievalService(vector_service=vector_service)
    pipeline = RetrievalPipeline(service=retrieval_svc)
    task_tool = TaskTool()
    
    # Check if user is asking about task creation or task status
    question_lower = question.lower()
    
    # Determine intent
    wants_task_creation = any(keyword in question_lower for keyword in [
        "create task", "add task", "new task", "make task", "schedule task", "task for"
    ])
    wants_task_status = any(keyword in question_lower for keyword in [
        "my tasks", "task status", "show tasks", "list tasks", "what tasks", "check tasks"
    ])
    wants_task_completion = any(keyword in question_lower for keyword in [
        "complete task", "finish task", "mark done", "task done", "completed task"
    ])
    
    # Handle task operations
    if wants_task_creation or wants_task_status or wants_task_completion:
        if wants_task_creation:
            # Check if we have enough info from conversation
            # For now, we'll use the LLM to extract task info and create it
            task_prompt = f"""
{ONBOARDING_SYSTEM_PROMPT}

{TASK_CREATION_PROMPT}

Current conversation:
{json.dumps(messages[-6:], indent=2)}

User's latest message: {question}

Respond with either:
1. A question to get missing information
2. A confirmation message summarizing the task to be created
3. A JSON object with the task details if user confirmed
"""
            
            # Get LLM response for task creation
            llm_messages = [
                {"role": "system", "content": task_prompt},
                {"role": "user", "content": question}
            ]
            
            llm_response = await llm_service.complete(llm_messages)
            response_content = llm_response.content
            
            # Try to parse JSON for task creation
            try:
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    task_data = json.loads(json_match.group())
                    # Create the task
                    result = await task_tool.execute(
                        operation=TaskOperation.CREATE,
                        user_id=user_id,
                        title=task_data.get("title"),
                        description=task_data.get("description"),
                        due_date=task_data.get("due_date"),
                        priority=task_data.get("priority", "medium"),
                    )
                    response_content = f"✅ Task created successfully!\n\n**{task_data.get('title')}**\n{task_data.get('description', '')}\n\nPriority: {task_data.get('priority', 'medium').capitalize()}\nDue: {task_data.get('due_date', 'Not set')}"
            except (json.JSONDecodeError, KeyError):
                pass  # Not a JSON response, just return the LLM response
            
            return {
                "answer": response_content,
                "selected_agent": "onboarding_agent",
                "citations": [],
                "model": llm_response.model,
                "provider": llm_response.provider,
                "prompt_tokens": llm_response.usage.prompt_tokens,
                "completion_tokens": llm_response.usage.completion_tokens,
                "latency_ms": llm_response.latency_ms,
                "messages": messages + [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response_content}
                ],
            }
        
        elif wants_task_status:
            # List user's tasks
            result = await task_tool.execute(
                operation=TaskOperation.LIST,
                user_id=user_id,
            )
            
            if result.tasks:
                task_list = "\n".join([
                    f"- **{t['title']}** ({t['status']}) - Priority: {t['priority']}"
                    + (f", Due: {t['due_date']}" if t.get('due_date') else "")
                    for t in result.tasks
                ])
                response = f"Here are your current onboarding tasks:\n\n{task_list}"
            else:
                response = "You don't have any onboarding tasks yet. Would you like to create one?"
            
            return {
                "answer": response,
                "selected_agent": "onboarding_agent",
                "citations": [],
                "model": "",
                "provider": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency_ms": 0,
                "messages": messages + [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response}
                ],
            }
        
        elif wants_task_completion:
            # Ask which task to complete
            result = await task_tool.execute(
                operation=TaskOperation.LIST,
                user_id=user_id,
            )
            
            if not result.tasks:
                response = "You don't have any tasks to complete."
            else:
                task_list = "\n".join([
                    f"- {t['title']} (ID: {t['task_id'][:8]}...)"
                    for t in result.tasks if t['status'] != 'completed'
                ])
                response = f"Which task would you like to mark as complete?\n\n{task_list}\n\nPlease provide the task title or ID."
            
            return {
                "answer": response,
                "selected_agent": "onboarding_agent",
                "citations": [],
                "model": "",
                "provider": "",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency_ms": 0,
                "messages": messages + [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": response}
                ],
            }
    
    # Regular Q&A - run retrieval pipeline
    retrieval_cfg = RetrievalConfig(
        top_k_search=20,
        top_k_rerank=5,
        min_score=0.3,
        department=None,
        document_id=None,
    )
    
    retrieval_result = await pipeline.run(question, retrieval_cfg)
    
    # Build messages with context
    history = messages[-settings.conversation_history_window * 2:] if messages else []
    history_dicts = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in history]
    
    builder = PromptBuilder()
    base_messages = builder.build_messages(retrieval_result.context, question)
    
    messages_for_llm = (
        [base_messages[0]]  # system
        + history_dicts
        + [base_messages[1]]  # current user message with context
    )
    
    # Call LLM
    llm_response = await llm_service.complete(messages_for_llm)
    
    citations = retrieval_result.citations
    
    return {
        "answer": llm_response.content,
        "selected_agent": "onboarding_agent",
        "retrieved_context": retrieval_result.context,
        "citations": [c.model_dump() if hasattr(c, 'model_dump') else c for c in citations],
        "model": llm_response.model,
        "provider": llm_response.provider,
        "prompt_tokens": llm_response.usage.prompt_tokens,
        "completion_tokens": llm_response.usage.completion_tokens,
        "latency_ms": llm_response.latency_ms,
        "messages": messages + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": llm_response.content}
        ],
    }