"""Task management tool for HR Onboarding Agent."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskOperation(str, Enum):
    CREATE = "create"
    LIST = "list"
    UPDATE = "update"
    COMPLETE = "complete"
    DELETE = "delete"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCategory(str, Enum):
    HR = "HR"
    IT = "IT"
    FINANCE = "Finance"
    COMPLIANCE = "Compliance"
    GENERAL = "General"


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str = ""
    category: str = "HR"
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


class TaskToolResult(BaseModel):
    success: bool
    tasks: list[dict[str, Any]] = []
    message: str = ""
    task_id: Optional[str] = None


# In-memory task store
_task_store: dict[str, list[Task]] = {}


def _create_default_seed_tasks(user_id: str) -> list[Task]:
    """Create default initial onboarding tasks for a new hire."""
    now = datetime.utcnow()
    d3 = (now + timedelta(days=3)).strftime("%Y-%m-%d")
    d7 = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    d14 = (now + timedelta(days=14)).strftime("%Y-%m-%d")
    d30 = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    return [
        Task(
            user_id=user_id,
            title="Complete I-9 Employment Eligibility Verification",
            description="Upload identity and work authorization documents to the onboarding portal.",
            category="HR",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            due_date=d3,
        ),
        Task(
            user_id=user_id,
            title="Set up 1Password & MFA Authentication",
            description="Install 1Password and configure Multi-Factor Authentication for company email and VPN.",
            category="IT",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
            due_date=d3,
            completed_at=now.isoformat(),
        ),
        Task(
            user_id=user_id,
            title="Submit W-4 & Direct Deposit Details",
            description="Fill out payroll tax withholding and provide checking account routing number.",
            category="Finance",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            due_date=d7,
        ),
        Task(
            user_id=user_id,
            title="Review OptiAgent Employee Handbook & Policies",
            description="Read the Code of Conduct, Leave Policy, and Remote Work guidelines.",
            category="Compliance",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            due_date=d14,
        ),
        Task(
            user_id=user_id,
            title="Schedule 30-Day Check-in with Manager",
            description="Set up an informal 30-day alignment meeting with your People Manager.",
            category="HR",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            due_date=d30,
        ),
    ]


class TaskTool:
    """Tool for managing onboarding tasks."""

    def _ensure_user_seeded(self, user_id: str) -> list[Task]:
        if user_id not in _task_store or len(_task_store[user_id]) == 0:
            _task_store[user_id] = _create_default_seed_tasks(user_id)
        return _task_store[user_id]

    async def execute(
        self,
        operation: TaskOperation,
        user_id: str,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        due_date: Optional[str] = None,
    ) -> TaskToolResult:
        """Execute a task operation."""
        user_tasks = self._ensure_user_seeded(user_id)

        if operation == TaskOperation.CREATE:
            if not title:
                return TaskToolResult(
                    success=False,
                    message="Task title is required",
                )

            task = Task(
                user_id=user_id,
                title=title,
                description=description or "",
                category=category or "HR",
                status=status or TaskStatus.PENDING,
                priority=priority or TaskPriority.MEDIUM,
                due_date=due_date,
            )
            user_tasks.insert(0, task)

            return TaskToolResult(
                success=True,
                tasks=[task.model_dump()],
                message="Task created successfully",
                task_id=task.task_id,
            )

        elif operation == TaskOperation.LIST:
            sorted_tasks = sorted(user_tasks, key=lambda t: t.created_at, reverse=True)
            return TaskToolResult(
                success=True,
                tasks=[t.model_dump() for t in sorted_tasks],
                message=f"Found {len(sorted_tasks)} tasks",
            )

        elif operation == TaskOperation.UPDATE:
            target = None
            if task_id:
                for t in user_tasks:
                    if t.task_id == task_id or t.task_id.startswith(task_id):
                        target = t
                        break
            elif title:
                for t in user_tasks:
                    if title.lower() in t.title.lower():
                        target = t
                        break

            if not target:
                return TaskToolResult(
                    success=False,
                    message=f"Task not found: {task_id or title}",
                )

            if title is not None and task_id:
                target.title = title
            if description is not None:
                target.description = description
            if category is not None:
                target.category = category
            if status is not None:
                target.status = status
                if status == TaskStatus.COMPLETED:
                    target.completed_at = datetime.utcnow().isoformat()
            if priority is not None:
                target.priority = priority
            if due_date is not None:
                target.due_date = due_date
            target.updated_at = datetime.utcnow().isoformat()

            return TaskToolResult(
                success=True,
                tasks=[target.model_dump()],
                message="Task updated successfully",
                task_id=target.task_id,
            )

        elif operation == TaskOperation.COMPLETE:
            target = None
            if task_id:
                for t in user_tasks:
                    if t.task_id == task_id or t.task_id.startswith(task_id):
                        target = t
                        break
            if not target and title:
                for t in user_tasks:
                    if title.lower() in t.title.lower() or t.title.lower() in title.lower():
                        target = t
                        break

            if not target:
                # Try finding any non-completed task matching words in title
                if title:
                    query_words = [w for w in title.lower().split() if len(w) > 3]
                    for t in user_tasks:
                        if t.status != TaskStatus.COMPLETED and any(w in t.title.lower() for w in query_words):
                            target = t
                            break

            if not target:
                return TaskToolResult(
                    success=False,
                    message=f"Task not found to complete: {task_id or title}",
                )

            target.status = TaskStatus.COMPLETED
            target.completed_at = datetime.utcnow().isoformat()
            target.updated_at = datetime.utcnow().isoformat()

            return TaskToolResult(
                success=True,
                tasks=[target.model_dump()],
                message=f"Task '{target.title}' marked as completed",
                task_id=target.task_id,
            )

        elif operation == TaskOperation.DELETE:
            for i, task in enumerate(user_tasks):
                if task.task_id == task_id or (title and title.lower() in task.title.lower()):
                    deleted = user_tasks.pop(i)
                    return TaskToolResult(
                        success=True,
                        tasks=[deleted.model_dump()],
                        message="Task deleted successfully",
                        task_id=deleted.task_id,
                    )

            return TaskToolResult(
                success=False,
                message=f"Task not found: {task_id or title}",
            )

        return TaskToolResult(
            success=False,
            message=f"Unknown operation: {operation}",
        )