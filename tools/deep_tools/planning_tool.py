"""Planning Tool - Deep Agents SDK write_todos implementation.

This module provides task planning and breakdown capabilities, allowing agents
to create structured task lists for complex workflows.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStep(BaseModel):
    """A single step in a task breakdown.

    Attributes:
        step: Step number (1-indexed)
        action: Description of the action to perform
        status: Current status of the task
        agent: Optional agent responsible for this step
        dependencies: Optional list of step numbers this depends on
    """
    step: int = Field(..., description="Step number")
    action: str = Field(..., description="Action description")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    agent: Optional[str] = Field(default=None, description="Responsible agent")
    dependencies: Optional[List[int]] = Field(default=None, description="Dependent step numbers")


def write_todos(task_description: str, context: Optional[Dict[str, Any]] = None) -> List[TaskStep]:
    """Break down a task into actionable steps.

    This is a simplified implementation of the Deep Agents SDK write_todos tool.
    In a production system, this would use an LLM to generate context-aware task breakdowns.
    For the MVP, we use rule-based patterns.

    Args:
        task_description: Natural language description of the task
        context: Optional context for task planning (e.g., current state, available resources)

    Returns:
        List of TaskStep objects representing the breakdown
    """
    logger.info(f"Planning task: {task_description}")

    task_lower = task_description.lower()

    # Pattern 1: Purchase Order Workflow
    if any(keyword in task_lower for keyword in ["purchase order", "create po", "order", "reorder"]):
        tasks = [
            TaskStep(
                step=1,
                action="Check inventory levels and identify items below reorder point",
                status=TaskStatus.PENDING,
                agent="inventory_monitor"
            ),
            TaskStep(
                step=2,
                action="Query suppliers for quotes and pricing",
                status=TaskStatus.PENDING,
                agent="supplier_selector",
                dependencies=[1]
            ),
            TaskStep(
                step=3,
                action="Compare supplier offers and select best options",
                status=TaskStatus.PENDING,
                agent="supplier_selector",
                dependencies=[2]
            ),
            TaskStep(
                step=4,
                action="Generate purchase order documents with tax calculations",
                status=TaskStatus.PENDING,
                agent="purchase_order",
                dependencies=[3]
            ),
            TaskStep(
                step=5,
                action="Validate purchase orders (high-value orders only)",
                status=TaskStatus.PENDING,
                agent="purchase_order.validator",
                dependencies=[4]
            ),
            TaskStep(
                step=6,
                action="Save purchase orders to filesystem",
                status=TaskStatus.PENDING,
                agent="purchase_order",
                dependencies=[5]
            )
        ]
        logger.info(f"Generated {len(tasks)} steps for purchase order workflow")
        return tasks

    # Pattern 2: Inventory Check Only
    if any(keyword in task_lower for keyword in ["check inventory", "inventory status", "stock level"]):
        tasks = [
            TaskStep(
                step=1,
                action="Load inventory data from CSV",
                status=TaskStatus.PENDING,
                agent="inventory_monitor"
            ),
            TaskStep(
                step=2,
                action="Check stock levels against reorder points",
                status=TaskStatus.PENDING,
                agent="inventory_monitor",
                dependencies=[1]
            ),
            TaskStep(
                step=3,
                action="Calculate recommended reorder quantities",
                status=TaskStatus.PENDING,
                agent="inventory_monitor",
                dependencies=[2]
            )
        ]
        logger.info(f"Generated {len(tasks)} steps for inventory check workflow")
        return tasks

    # Pattern 3: Supplier Selection Only
    if any(keyword in task_lower for keyword in ["supplier", "quote", "pricing"]):
        tasks = [
            TaskStep(
                step=1,
                action="Load supplier data",
                status=TaskStatus.PENDING,
                agent="supplier_selector"
            ),
            TaskStep(
                step=2,
                action="Collect quotes from all suppliers",
                status=TaskStatus.PENDING,
                agent="supplier_selector",
                dependencies=[1]
            ),
            TaskStep(
                step=3,
                action="Analyze and recommend best suppliers",
                status=TaskStatus.PENDING,
                agent="supplier_selector",
                dependencies=[2]
            )
        ]
        logger.info(f"Generated {len(tasks)} steps for supplier selection workflow")
        return tasks

    # Default: Generic task breakdown
    tasks = [
        TaskStep(
            step=1,
            action=f"Parse and understand task: {task_description}",
            status=TaskStatus.PENDING
        ),
        TaskStep(
            step=2,
            action="Execute primary task action",
            status=TaskStatus.PENDING,
            dependencies=[1]
        ),
        TaskStep(
            step=3,
            action="Validate and return results",
            status=TaskStatus.PENDING,
            dependencies=[2]
        )
    ]
    logger.info(f"Generated {len(tasks)} steps for generic workflow")
    return tasks


def format_task_list(tasks: List[TaskStep], show_agent: bool = False) -> str:
    """Format a task list for display.

    Args:
        tasks: List of TaskStep objects
        show_agent: Whether to show the responsible agent for each task

    Returns:
        Formatted string representation of the task list
    """
    status_symbols = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌"
    }

    lines = ["📋 Task Breakdown:"]
    for task in tasks:
        symbol = status_symbols.get(task.status, "⏳")
        agent_info = f" [{task.agent}]" if show_agent and task.agent else ""
        lines.append(f"{task.step}. {symbol} {task.action}{agent_info}")

    return "\n".join(lines)


def update_task_status(
    tasks: List[TaskStep],
    step_number: int,
    new_status: TaskStatus
) -> List[TaskStep]:
    """Update the status of a specific task step.

    Args:
        tasks: List of TaskStep objects
        step_number: Step number to update
        new_status: New status to set

    Returns:
        Updated list of tasks
    """
    for task in tasks:
        if task.step == step_number:
            old_status = task.status
            task.status = new_status
            logger.debug(f"Task {step_number} status: {old_status} -> {new_status}")
            break

    return tasks


def get_next_task(tasks: List[TaskStep]) -> Optional[TaskStep]:
    """Get the next pending task that has all dependencies met.

    Args:
        tasks: List of TaskStep objects

    Returns:
        Next task to execute, or None if no tasks are ready
    """
    completed_steps = {task.step for task in tasks if task.status == TaskStatus.COMPLETED}

    for task in tasks:
        if task.status != TaskStatus.PENDING:
            continue

        # Check if all dependencies are met
        if task.dependencies:
            if all(dep in completed_steps for dep in task.dependencies):
                return task
        else:
            # No dependencies, task is ready
            return task

    return None
