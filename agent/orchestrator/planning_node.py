"""Planning Node - Deep Agents SDK integration for task planning.

This module provides a planning node for the orchestrator agent that uses
the Deep Agents planning tool to break down user requests into actionable tasks.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools.deep_tools.planning_tool import (
    write_todos,
    format_task_list,
    update_task_status,
    get_next_task,
    TaskStep,
    TaskStatus,
)
from agent.orchestrator.models import OrchestratorState

logger = logging.getLogger(__name__)


class PlanningContext:
    """Context for planning operations.

    Maintains state about the current plan and its execution progress.

    Attributes:
        task_description: Original task description
        tasks: List of planned tasks
        current_task_index: Index of currently executing task
        started_at: When planning started
        completed_tasks: Count of completed tasks
    """

    def __init__(self, task_description: str):
        """Initialize planning context.

        Args:
            task_description: Description of the task to plan
        """
        self.task_description = task_description
        self.tasks: List[TaskStep] = []
        self.current_task_index: int = 0
        self.started_at: datetime = datetime.now()
        self.completed_tasks: int = 0

    def create_plan(self, context: Optional[Dict[str, Any]] = None) -> List[TaskStep]:
        """Create a plan for the task.

        Args:
            context: Optional additional context for planning

        Returns:
            List of planned tasks
        """
        self.tasks = write_todos(self.task_description, context)
        logger.info(f"Created plan with {len(self.tasks)} tasks")
        return self.tasks

    def get_current_task(self) -> Optional[TaskStep]:
        """Get the current task to execute.

        Returns:
            Current task or None if all tasks complete
        """
        return get_next_task(self.tasks)

    def mark_task_complete(self, step_number: int) -> None:
        """Mark a task as complete.

        Args:
            step_number: Step number to mark complete
        """
        self.tasks = update_task_status(self.tasks, step_number, TaskStatus.COMPLETED)
        self.completed_tasks += 1
        logger.info(f"Task {step_number} completed ({self.completed_tasks}/{len(self.tasks)})")

    def mark_task_in_progress(self, step_number: int) -> None:
        """Mark a task as in progress.

        Args:
            step_number: Step number to mark in progress
        """
        self.tasks = update_task_status(self.tasks, step_number, TaskStatus.IN_PROGRESS)

    def mark_task_failed(self, step_number: int) -> None:
        """Mark a task as failed.

        Args:
            step_number: Step number to mark failed
        """
        self.tasks = update_task_status(self.tasks, step_number, TaskStatus.FAILED)

    def get_progress(self) -> Dict[str, Any]:
        """Get planning progress.

        Returns:
            Progress dictionary
        """
        return {
            "total_tasks": len(self.tasks),
            "completed": self.completed_tasks,
            "pending": len(self.tasks) - self.completed_tasks,
            "progress_percent": round(
                self.completed_tasks / len(self.tasks) * 100, 1
            ) if self.tasks else 0
        }

    def format_plan(self, show_agent: bool = True) -> str:
        """Format the plan for display.

        Args:
            show_agent: Whether to show assigned agents

        Returns:
            Formatted plan string
        """
        return format_task_list(self.tasks, show_agent=show_agent)


# Global planning context
_current_planning_context: Optional[PlanningContext] = None


def planning_node(state: OrchestratorState) -> Dict[str, Any]:
    """Planning node for the orchestrator workflow.

    This node uses the Deep Agents planning tool to break down user requests
    into actionable tasks before execution begins.

    Args:
        state: Current orchestrator state

    Returns:
        State update with planning information
    """
    global _current_planning_context

    user_message = state.get("user_message", "")
    workflow_stage = state.get("workflow_stage", "initial")

    # Only plan at the start of a new workflow
    if workflow_stage != "initial":
        logger.debug("Skipping planning - workflow already in progress")
        return {}

    # Determine task description from user message
    task_description = _extract_task_description(user_message)

    if not task_description:
        logger.debug("No actionable task detected, skipping planning")
        return {}

    # Create new planning context
    logger.info(f"[Planning] Creating plan for: {task_description}")
    _current_planning_context = PlanningContext(task_description)

    # Generate plan
    context = {
        "conversation_history": state.get("conversation_history", []),
        "current_inventory": state.get("reorder_recommendations", []),
    }
    tasks = _current_planning_context.create_plan(context)

    # Format plan for display
    plan_display = _current_planning_context.format_plan(show_agent=False)

    logger.info(f"[Planning] Generated {len(tasks)} tasks")
    for task in tasks:
        logger.debug(f"  Step {task.step}: {task.action}")

    # Add plan to metadata
    metadata = state.get("metadata", {})
    metadata["planning"] = {
        "task_description": task_description,
        "task_count": len(tasks),
        "plan_created_at": datetime.now().isoformat(),
        "tasks": [
            {
                "step": t.step,
                "action": t.action,
                "agent": t.agent,
                "status": t.status.value
            }
            for t in tasks
        ]
    }

    return {
        "metadata": metadata,
        "plan_display": plan_display,
    }


def _extract_task_description(user_message: str) -> Optional[str]:
    """Extract a task description from user message.

    Args:
        user_message: User's input message

    Returns:
        Task description or None if not actionable
    """
    message_lower = user_message.lower()

    # Check for inventory-related tasks
    if any(kw in message_lower for kw in ["check inventory", "inventory check", "stock level"]):
        return "check inventory levels and identify items needing reorder"

    # Check for PO-related tasks
    if any(kw in message_lower for kw in ["create po", "purchase order", "order", "reorder"]):
        return "create purchase orders for low stock items"

    # Check for supplier-related tasks
    if any(kw in message_lower for kw in ["supplier", "quote", "pricing", "compare"]):
        return "get supplier quotes and compare pricing"

    return None


def update_current_task_status(
    step_number: int,
    status: TaskStatus
) -> None:
    """Update the status of a task in the current plan.

    Args:
        step_number: Step number to update
        status: New status
    """
    global _current_planning_context

    if _current_planning_context is None:
        logger.warning("No active planning context")
        return

    if status == TaskStatus.COMPLETED:
        _current_planning_context.mark_task_complete(step_number)
    elif status == TaskStatus.IN_PROGRESS:
        _current_planning_context.mark_task_in_progress(step_number)
    elif status == TaskStatus.FAILED:
        _current_planning_context.mark_task_failed(step_number)


def get_current_plan() -> Optional[PlanningContext]:
    """Get the current planning context.

    Returns:
        Current PlanningContext or None
    """
    return _current_planning_context


def clear_planning_context() -> None:
    """Clear the current planning context."""
    global _current_planning_context
    _current_planning_context = None
    logger.debug("Planning context cleared")


def format_planning_progress() -> str:
    """Format the current planning progress for display.

    Returns:
        Formatted progress string
    """
    global _current_planning_context

    if _current_planning_context is None:
        return "No active plan"

    progress = _current_planning_context.get_progress()
    plan = _current_planning_context.format_plan(show_agent=False)

    return f"{plan}\n\nProgress: {progress['completed']}/{progress['total_tasks']} ({progress['progress_percent']}%)"
