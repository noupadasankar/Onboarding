"""Task management tool for HR Onboarding Agent."""
from __future__ import annotations

import uuid
from datetime import datetime
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


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str = ""
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


# In-memory task store (replace with database in production)
_task_store: dict[str, list[Task]] = {}


class TaskTool:
    """Tool for managing onboarding tasks."""
    
    async def execute(
        self,
        operation: TaskOperation,
        user_id: str,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        due_date: Optional[str] = None,
    ) -> TaskToolResult:
        """Execute a task operation."""
        if user_id not in _task_store:
            _task_store[user_id] = []
        
        user_tasks = _task_store[user_id]
        
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
                priority=priority or TaskPriority.MEDIUM,
                due_date=due_date,
            )
            user_tasks.append(task)
            
            return TaskToolResult(
                success=True,
                tasks=[task.model_dump()],
                message="Task created successfully",
                task_id=task.task_id,
            )
        
        elif operation == TaskOperation.LIST:
            # Sort by created_at descending
            sorted_tasks = sorted(user_tasks, key=lambda t: t.created_at, reverse=True)
            return TaskToolResult(
                success=True,
                tasks=[t.model_dump() for t in sorted_tasks],
                message=f"Found {len(sorted_tasks)} tasks",
            )
        
        elif operation == TaskOperation.UPDATE:
            if not task_id:
                return TaskToolResult(
                    success=False,
                    message="Task ID is required for update",
                )
            
            for i, task in enumerate(user_tasks):
                if task.task_id == task_id:
                    if title is not None:
                        task.title = title
                    if description is not None:
                        task.description = description
                    if status is not None:
                        task.status = status
                        if status == TaskStatus.COMPLETED:
                            task.completed_at = datetime.utcnow().isoformat()
                    if priority is not None:
                        task.priority = priority
                    if due_date is not None:
                        task.due_date = due_date
                    task.updated_at = datetime.utcnow().isoformat()
                    user_tasks[i] = task
                    
                    return TaskToolResult(
                        success=True,
                        tasks=[task.model_dump()],
                        message="Task updated successfully",
                        task_id=task_id,
                    )
            
            return TaskToolResult(
                success=False,
                message=f"Task not found: {task_id}",
            )
        
        elif operation == TaskOperation.COMPLETE:
            if not task_id:
                return TaskToolResult(
                    success=False,
                    message="Task ID is required to complete",
                )
            
            for i, task in enumerate(user_tasks):
                if task.task_id == task_id:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow().isoformat()
                    task.updated_at = datetime.utcnow().isoformat()
                    user_tasks[i] = task
                    
                    return TaskToolResult(
                        success=True,
                        tasks=[task.model_dump()],
                        message="Task marked as completed",
                        task_id=task_id,
                    )
            
            return TaskToolResult(
                success=False,
                message=f"Task not found: {task_id}",
            )
        
        elif operation == TaskOperation.DELETE:
            if not task_id:
                return TaskToolResult(
                    success=False,
                    message="Task ID is required for deletion",
                )
            
            for i, task in enumerate(user_tasks):
                if task.task_id == task_id:
                    user_tasks.pop(i)
                    return TaskToolResult(
                        success=True,
                        message="Task deleted successfully",
                        task_id=task_id,
                    )
            
            return TaskToolResult(
                success=False,
                message=f"Task not found: {task_id}",
            )
        
        return TaskToolResult(
            success=False,
            message=f"Unknown operation: {operation}",
        )