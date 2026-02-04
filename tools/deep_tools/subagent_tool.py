"""SubAgent Tool - Deep Agents SDK sub-agent spawning implementation.

This module provides the task tool for spawning sub-agents, enabling
hierarchical agent structures and specialized task delegation.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError

logger = logging.getLogger(__name__)


class SubAgentType(str, Enum):
    """Types of sub-agents that can be spawned."""
    VALIDATOR = "validator"
    CALCULATOR = "calculator"
    SEARCHER = "searcher"
    ANALYZER = "analyzer"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """Status of a spawned task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskResult:
    """Result of a sub-agent task execution.

    Attributes:
        task_id: Unique task identifier
        status: Task status
        result: Task result data (if successful)
        error: Error message (if failed)
        started_at: When the task started
        completed_at: When the task completed
        duration_ms: Execution duration in milliseconds
    """
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None


@dataclass
class SpawnedTask:
    """Represents a spawned sub-agent task.

    Attributes:
        task_id: Unique task identifier
        agent_type: Type of sub-agent
        description: Task description
        input_data: Input data for the task
        handler: Function to execute
        status: Current status
        future: Async future (if running async)
    """
    task_id: str
    agent_type: SubAgentType
    description: str
    input_data: Dict[str, Any]
    handler: Callable
    status: TaskStatus = TaskStatus.PENDING
    future: Optional[Future] = None
    result: Optional[TaskResult] = None


class SubAgentSpawner:
    """Spawner for sub-agent tasks.

    Provides functionality to spawn, manage, and monitor sub-agent tasks.
    Supports both synchronous and asynchronous execution.

    Attributes:
        max_concurrent: Maximum concurrent tasks
        timeout_seconds: Default task timeout
        executor: Thread pool for async execution
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        timeout_seconds: float = 60.0
    ):
        """Initialize the sub-agent spawner.

        Args:
            max_concurrent: Maximum concurrent tasks
            timeout_seconds: Default timeout for tasks
        """
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

        self._active_tasks: Dict[str, SpawnedTask] = {}
        self._completed_tasks: List[TaskResult] = []
        self._handlers: Dict[str, Callable] = {}

        # Register default handlers
        self._register_default_handlers()

        logger.info(
            f"SubAgentSpawner initialized (max_concurrent={max_concurrent})"
        )

    def _register_default_handlers(self) -> None:
        """Register default sub-agent handlers."""

        # Validator handler
        def validator_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
            from agent.purchase_order.validator import validate_purchase_order
            from agent.purchase_order.models import PurchaseOrder

            po_data = input_data.get("purchase_order", {})
            if isinstance(po_data, dict):
                po = PurchaseOrder(**po_data)
            else:
                po = po_data

            result = validate_purchase_order(po)
            return {
                "is_valid": result.is_valid,
                "issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity.value}
                    for i in result.issues
                ]
            }

        self._handlers["validator"] = validator_handler

        # Calculator handler
        def calculator_handler(input_data: Dict[str, Any]) -> Dict[str, Any]:
            operation = input_data.get("operation", "sum")
            values = input_data.get("values", [])

            if operation == "sum":
                result = sum(values)
            elif operation == "avg":
                result = sum(values) / len(values) if values else 0
            elif operation == "max":
                result = max(values) if values else 0
            elif operation == "min":
                result = min(values) if values else 0
            else:
                result = 0

            return {"operation": operation, "result": result}

        self._handlers["calculator"] = calculator_handler

    def register_handler(
        self,
        agent_type: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Register a custom handler for an agent type.

        Args:
            agent_type: Agent type identifier
            handler: Handler function
        """
        self._handlers[agent_type] = handler
        logger.info(f"Registered handler for agent type: {agent_type}")

    def spawn_task(
        self,
        agent_type: str,
        description: str,
        input_data: Dict[str, Any],
        async_execution: bool = False,
        timeout: Optional[float] = None
    ) -> TaskResult:
        """Spawn a sub-agent task.

        Args:
            agent_type: Type of sub-agent to spawn
            description: Task description
            input_data: Input data for the task
            async_execution: Whether to run asynchronously
            timeout: Optional timeout override

        Returns:
            TaskResult with execution status and result
        """
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        timeout = timeout or self.timeout_seconds

        logger.info(f"[SubAgent] Spawning task: {task_id} ({agent_type})")
        logger.info(f"[SubAgent] Description: {description}")

        # Get handler
        handler = self._handlers.get(agent_type)
        if not handler:
            logger.error(f"No handler for agent type: {agent_type}")
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=f"No handler for agent type: {agent_type}"
            )

        # Create task
        task = SpawnedTask(
            task_id=task_id,
            agent_type=SubAgentType(agent_type) if agent_type in [e.value for e in SubAgentType] else SubAgentType.CUSTOM,
            description=description,
            input_data=input_data,
            handler=handler
        )

        self._active_tasks[task_id] = task

        # Execute
        if async_execution:
            return self._execute_async(task, timeout)
        else:
            return self._execute_sync(task, timeout)

    def _execute_sync(self, task: SpawnedTask, timeout: float) -> TaskResult:
        """Execute a task synchronously.

        Args:
            task: Task to execute
            timeout: Timeout in seconds

        Returns:
            TaskResult
        """
        task.status = TaskStatus.RUNNING
        started_at = datetime.now()

        try:
            # Execute handler
            result_data = task.handler(task.input_data)

            completed_at = datetime.now()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result_data,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms
            )

            logger.info(
                f"[SubAgent] Task {task.task_id} completed in {duration_ms:.2f}ms"
            )

        except Exception as e:
            completed_at = datetime.now()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms
            )

            logger.error(f"[SubAgent] Task {task.task_id} failed: {e}")

        # Cleanup
        task.result = result
        del self._active_tasks[task.task_id]
        self._completed_tasks.append(result)

        return result

    def _execute_async(self, task: SpawnedTask, timeout: float) -> TaskResult:
        """Execute a task asynchronously.

        Args:
            task: Task to execute
            timeout: Timeout in seconds

        Returns:
            TaskResult (may be pending if async)
        """
        task.status = TaskStatus.RUNNING
        started_at = datetime.now()

        # Submit to executor
        future = self.executor.submit(task.handler, task.input_data)
        task.future = future

        try:
            # Wait for result with timeout
            result_data = future.result(timeout=timeout)

            completed_at = datetime.now()
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result_data,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms
            )

        except TimeoutError:
            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.TIMEOUT,
                error=f"Task timed out after {timeout}s",
                started_at=started_at
            )
            logger.warning(f"[SubAgent] Task {task.task_id} timed out")

        except Exception as e:
            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                started_at=started_at
            )
            logger.error(f"[SubAgent] Task {task.task_id} failed: {e}")

        # Cleanup
        task.result = result
        del self._active_tasks[task.task_id]
        self._completed_tasks.append(result)

        return result

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks.

        Returns:
            List of active task summaries
        """
        return [
            {
                "task_id": t.task_id,
                "agent_type": t.agent_type.value,
                "description": t.description,
                "status": t.status.value
            }
            for t in self._active_tasks.values()
        ]

    def get_completed_tasks(self, limit: int = 20) -> List[TaskResult]:
        """Get recent completed tasks.

        Args:
            limit: Maximum tasks to return

        Returns:
            List of TaskResult objects
        """
        return self._completed_tasks[-limit:]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task.

        Args:
            task_id: Task to cancel

        Returns:
            True if cancelled, False if not found
        """
        task = self._active_tasks.get(task_id)
        if not task:
            return False

        if task.future:
            task.future.cancel()

        task.status = TaskStatus.CANCELLED
        del self._active_tasks[task_id]

        logger.info(f"[SubAgent] Task {task_id} cancelled")
        return True

    def shutdown(self) -> None:
        """Shutdown the spawner and executor."""
        logger.info("Shutting down SubAgentSpawner")
        self.executor.shutdown(wait=True)


# Global spawner instance
_subagent_spawner: Optional[SubAgentSpawner] = None


def get_subagent_spawner() -> SubAgentSpawner:
    """Get the global sub-agent spawner instance.

    Returns:
        SubAgentSpawner instance
    """
    global _subagent_spawner
    if _subagent_spawner is None:
        _subagent_spawner = SubAgentSpawner()
    return _subagent_spawner


def spawn_subagent(
    agent_type: str,
    description: str,
    input_data: Dict[str, Any],
    async_execution: bool = False
) -> TaskResult:
    """Spawn a sub-agent task.

    This is the main entry point for the Deep Agents task tool.

    Args:
        agent_type: Type of sub-agent to spawn
        description: Task description
        input_data: Input data for the task
        async_execution: Whether to run asynchronously

    Returns:
        TaskResult with execution status
    """
    spawner = get_subagent_spawner()
    return spawner.spawn_task(
        agent_type=agent_type,
        description=description,
        input_data=input_data,
        async_execution=async_execution
    )
