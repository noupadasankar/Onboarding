"""HR Onboarding Agent — handles onboarding Q&A and task management for new hires."""
from __future__ import annotations

import json
import re
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
from app.tools.task_tool import TaskTool, TaskOperation, TaskStatus, TaskPriority

_log = get_logger()

ONBOARDING_SYSTEM_PROMPT = """You are the HR Onboarding AI Employee — a warm, professional, and knowledgeable onboarding guide for new employees.

Your responsibilities:
1. Answer onboarding questions grounded strictly in the provided HR, IT, and company policy documents.
2. Help new hires track, manage, and complete their onboarding tasks.
3. Guide new hires through their Day 1, Week 1, and 30/60/90-day journey.

Rules for answering:
- Answer ONLY from the provided document context. If a detail is not in the context, politely state: "I couldn't find specific details for that in our onboarding documents, but you can reach out to your HR Business Partner at hr.global@optiagent.com."
- When citing policies, reference the document name and section clearly.
- Format answers cleanly with markdown headings, bullet points, and emoji badges for readability.
- Maintain conversation context across turns.
"""


async def onboarding_agent_node(
    state: GraphState,
    retrieval_tool: RetrievalTool,
    llm_service: LLMService,
) -> dict[str, Any]:
    """Onboarding agent node for LangGraph."""
    question = state.get("question", "").strip()
    user_id = state.get("user_id", "") or "default-user"
    conversation_id = state.get("conversation_id", "")
    messages = state.get("messages", [])

    settings = get_settings()
    vector_service = retrieval_tool.vector_service
    retrieval_svc = RetrievalService(vector_service=vector_service)
    pipeline = RetrievalPipeline(service=retrieval_svc)
    task_tool = TaskTool()

    question_lower = question.lower()

    # ── Intent Classification ──────────────────────────────────────────────────
    is_task_list_query = any(k in question_lower for k in [
        "what tasks", "my tasks", "show tasks", "list tasks", "task status",
        "check tasks", "onboarding checklist", "my checklist", "what do i need to do",
        "tasks remaining", "tasks left", "progress"
    ])

    is_task_complete_action = any(k in question_lower for k in [
        "mark done", "mark complete", "marked as complete", "mark as completed",
        "completed task", "finished task", "i finished", "i have completed",
        "complete task", "done with", "mark as done"
    ])

    is_task_create_action = any(k in question_lower for k in [
        "create task", "add task", "new task", "make a task", "schedule task",
        "add to my tasks", "add that to my tasks", "add this as a task",
        "remind me to", "create a task", "add a task"
    ])

    # ── Task Operation 1: List Tasks / Check Status ───────────────────────────
    if is_task_list_query and not is_task_create_action and not is_task_complete_action:
        result = await task_tool.execute(operation=TaskOperation.LIST, user_id=user_id)
        tasks = result.tasks
        completed = [t for t in tasks if t.get("status") == "completed"]
        in_progress = [t for t in tasks if t.get("status") == "in_progress"]
        pending = [t for t in tasks if t.get("status") == "pending"]

        pct = round((len(completed) / len(tasks) * 100)) if tasks else 0

        lines = [
            f"### 📋 Your Onboarding Task Checklist",
            f"**Overall Progress: {pct}% Complete** ({len(completed)} of {len(tasks)} tasks finished)\n",
        ]

        if in_progress:
            lines.append("#### ⏳ In Progress")
            for t in in_progress:
                due = f" (Due: {t['due_date']})" if t.get("due_date") else ""
                lines.append(f"- **{t['title']}** — Priority: `{t['priority'].upper()}` | Category: `{t.get('category', 'HR')}`{due}")

        if pending:
            lines.append("\n#### 📌 Pending")
            for t in pending:
                due = f" (Due: {t['due_date']})" if t.get("due_date") else ""
                lines.append(f"- **{t['title']}** — Priority: `{t['priority'].upper()}` | Category: `{t.get('category', 'HR')}`{due}")

        if completed:
            lines.append("\n#### ✅ Completed")
            for t in completed:
                lines.append(f"- ~~{t['title']}~~ — Completed")

        lines.append("\n💡 *Tip: You can tell me 'Mark [task name] as complete' or 'Add a task for [action]' anytime!*")
        response_text = "\n".join(lines)

        return {
            "answer": response_text,
            "selected_agent": "onboarding_agent",
            "citations": [],
            "model": "task_service",
            "provider": "system",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 10.0,
            "messages": messages + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response_text},
            ],
        }

    # ── Task Operation 2: Mark Task Complete ──────────────────────────────────
    if is_task_complete_action:
        # Extract task title from input using LLM or direct regex
        target_name = question
        for prefix in ["mark", "as complete", "as completed", "as done", "completed", "finished", "i have", "task"]:
            target_name = re.sub(rf"\b{prefix}\b", "", target_name, flags=re.IGNORECASE)
        target_name = target_name.strip(" !.,?:;\"'")

        result = await task_tool.execute(
            operation=TaskOperation.COMPLETE,
            user_id=user_id,
            title=target_name or question,
        )

        if result.success and result.tasks:
            completed_task = result.tasks[0]
            # List remaining tasks
            list_res = await task_tool.execute(operation=TaskOperation.LIST, user_id=user_id)
            total = len(list_res.tasks)
            done_count = len([t for t in list_res.tasks if t.get("status") == "completed"])
            pct = round((done_count / total * 100)) if total else 100

            response_text = (
                f"🎉 **Great progress!** I've marked **\"{completed_task['title']}\"** as **Completed**.\n\n"
                f"📊 Your onboarding progress is now **{pct}%** ({done_count}/{total} tasks complete).\n\n"
                f"Let me know if you need help with your next pending tasks or have questions about policies!"
            )
        else:
            response_text = (
                f"I couldn't identify which specific task to mark as complete. "
                f"You can say *\"Show my tasks\"* to see your current list, then *\"Mark [Task Name] as done\"*."
            )

        return {
            "answer": response_text,
            "selected_agent": "onboarding_agent",
            "citations": [],
            "model": "task_service",
            "provider": "system",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 15.0,
            "messages": messages + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response_text},
            ],
        }

    # ── Task Operation 3: Create Task ─────────────────────────────────────────
    if is_task_create_action:
        # Use LLM to extract task parameters contextually from multi-turn history
        extraction_prompt = f"""You are an HR task extraction assistant.
Extract task details from the user's request and prior conversation context.

Conversation history:
{json.dumps(messages[-4:], indent=2)}

User request: "{question}"

Output JSON ONLY with this structure:
{{
  "title": "Clear concise task title",
  "description": "Brief description or empty string",
  "category": "HR" | "IT" | "Finance" | "Compliance",
  "priority": "low" | "medium" | "high",
  "due_date": "YYYY-MM-DD" or null
}}
"""
        extract_response = await llm_service.complete([
            {"role": "system", "content": "You output valid JSON only."},
            {"role": "user", "content": extraction_prompt},
        ])

        try:
            json_match = re.search(r"\{.*\}", extract_response.content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                title = data.get("title") or question
                cat = data.get("category", "HR")
                prio = data.get("priority", "medium").lower()
                due = data.get("due_date")

                res = await task_tool.execute(
                    operation=TaskOperation.CREATE,
                    user_id=user_id,
                    title=title,
                    description=data.get("description", ""),
                    category=cat,
                    priority=TaskPriority(prio) if prio in ["low", "medium", "high"] else TaskPriority.MEDIUM,
                    due_date=due,
                )

                response_text = (
                    f"✅ **Task Created Successfully!**\n\n"
                    f"📌 **{title}**\n"
                    f"- **Category**: `{cat}`\n"
                    f"- **Priority**: `{prio.capitalize()}`\n"
                    f"- **Due Date**: `{due if due else 'Within first 2 weeks'}`\n\n"
                    f"This has been added to your Onboarding Checklist. Ask me *'Show my tasks'* anytime to view your progress!"
                )
            else:
                response_text = "I've noted that! What title would you like to give to this onboarding task?"
        except Exception:
            res = await task_tool.execute(
                operation=TaskOperation.CREATE,
                user_id=user_id,
                title=question,
                category="HR",
            )
            response_text = f"✅ Created task: **{question}** on your onboarding checklist."

        return {
            "answer": response_text,
            "selected_agent": "onboarding_agent",
            "citations": [],
            "model": extract_response.model,
            "provider": extract_response.provider,
            "prompt_tokens": extract_response.usage.prompt_tokens,
            "completion_tokens": extract_response.usage.completion_tokens,
            "latency_ms": extract_response.latency_ms,
            "messages": messages + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": response_text},
            ],
        }

    # ── Standard Grounded Q&A via RAG ──────────────────────────────────────────
    retrieval_cfg = RetrievalConfig(
        top_k_search=15,
        top_k_rerank=5,
        min_score=0.25,
        department=None,
        document_id=None,
    )

    retrieval_result = await pipeline.run(question, retrieval_cfg)

    # Build prompt with retrieved context
    history = messages[-settings.conversation_history_window * 2:] if messages else []
    history_dicts = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in history]

    builder = PromptBuilder()
    base_messages = builder.build_messages(retrieval_result.context, question)

    # Insert system prompt enhancement
    system_msg = {
        "role": "system",
        "content": (
            f"{ONBOARDING_SYSTEM_PROMPT}\n\n"
            f"RETRIEVED ONBOARDING CONTEXT:\n{retrieval_result.context}\n\n"
            "INSTRUCTIONS:\n"
            "- Provide accurate, helpful answers based on the context above.\n"
            "- Always cite the source document and section name.\n"
            "- If applicable, mention relevant onboarding steps or timelines (Day 1, Week 1, 30 days).\n"
            "- If the question discusses an action item (e.g. enrolling in benefits or setting up VPN), offer to create a task."
        ),
    }

    messages_for_llm = [system_msg] + history_dicts + [{"role": "user", "content": question}]

    # Complete LLM call
    llm_response = await llm_service.complete(messages_for_llm)

    citations = retrieval_result.citations

    return {
        "answer": llm_response.content,
        "selected_agent": "onboarding_agent",
        "retrieved_context": retrieval_result.context,
        "citations": [c.model_dump() if hasattr(c, "model_dump") else c for c in citations],
        "model": llm_response.model,
        "provider": llm_response.provider,
        "prompt_tokens": llm_response.usage.prompt_tokens,
        "completion_tokens": llm_response.usage.completion_tokens,
        "latency_ms": llm_response.latency_ms,
        "messages": messages + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": llm_response.content},
        ],
    }