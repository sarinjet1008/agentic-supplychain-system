"""Validator Spawner - Sub-agent spawning for PO validation.

This module provides functionality to spawn validator sub-agents for
purchase order validation, demonstrating the Deep Agents sub-agent pattern.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from agent.purchase_order.validator import (
    validate_purchase_order,
    ValidationResult,
    ValidationSeverity,
)
from agent.purchase_order.models import PurchaseOrder

logger = logging.getLogger(__name__)


class SubAgentStatus(str, Enum):
    """Status of a sub-agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SubAgentTask:
    """Represents a sub-agent task.

    Attributes:
        task_id: Unique identifier for the task
        agent_type: Type of sub-agent to spawn
        input_data: Input data for the sub-agent
        status: Current status of the task
        result: Result from the sub-agent (if completed)
        error: Error message (if failed)
        created_at: When the task was created
        completed_at: When the task completed
    """
    task_id: str
    agent_type: str
    input_data: Dict[str, Any]
    status: SubAgentStatus = SubAgentStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ValidatorSpawner:
    """Spawns and manages validator sub-agents for PO validation.

    This class demonstrates the Deep Agents SDK sub-agent spawning pattern,
    allowing the PO agent to delegate validation to specialized sub-agents.

    Attributes:
        active_tasks: Dictionary of active sub-agent tasks
        completed_tasks: History of completed tasks
        config: Configuration settings
    """

    def __init__(
        self,
        high_value_threshold: float = 5000.0,
        max_concurrent_tasks: int = 5,
        validation_timeout_seconds: int = 30
    ):
        """Initialize the validator spawner.

        Args:
            high_value_threshold: Threshold for high-value order validation
            max_concurrent_tasks: Maximum concurrent sub-agents
            validation_timeout_seconds: Timeout for validation tasks
        """
        self.high_value_threshold = high_value_threshold
        self.max_concurrent_tasks = max_concurrent_tasks
        self.validation_timeout_seconds = validation_timeout_seconds

        self.active_tasks: Dict[str, SubAgentTask] = {}
        self.completed_tasks: List[SubAgentTask] = []

        logger.info(
            f"ValidatorSpawner initialized with high_value_threshold=${high_value_threshold}"
        )

    def should_spawn_validator(self, po: PurchaseOrder) -> bool:
        """Determine if a PO requires validator sub-agent.

        Args:
            po: Purchase order to check

        Returns:
            True if validation sub-agent should be spawned
        """
        # Always validate high-value orders
        if po.total_amount > self.high_value_threshold:
            logger.info(
                f"PO {po.po_number} is high-value (${po.total_amount:.2f}), "
                "spawning validator"
            )
            return True

        # Validate if there are many line items
        if len(po.line_items) > 10:
            logger.info(
                f"PO {po.po_number} has {len(po.line_items)} line items, "
                "spawning validator"
            )
            return True

        # Validate new suppliers
        known_suppliers = {"SUP001", "SUP002", "SUP003"}
        if po.supplier_id not in known_suppliers:
            logger.info(
                f"PO {po.po_number} uses unknown supplier {po.supplier_id}, "
                "spawning validator"
            )
            return True

        return False

    def spawn_validator(
        self,
        po: PurchaseOrder,
        additional_checks: Optional[List[str]] = None
    ) -> SubAgentTask:
        """Spawn a validator sub-agent for a purchase order.

        Args:
            po: Purchase order to validate
            additional_checks: Optional list of additional validation checks

        Returns:
            SubAgentTask representing the spawned sub-agent
        """
        task_id = f"val-{uuid.uuid4().hex[:8]}"

        task = SubAgentTask(
            task_id=task_id,
            agent_type="purchase_order.validator",
            input_data={
                "po_number": po.po_number,
                "po_data": po.model_dump() if hasattr(po, 'model_dump') else po.dict(),
                "additional_checks": additional_checks or []
            }
        )

        logger.info(f"[SubAgent] Spawning validator task: {task_id}")
        logger.info(f"[SubAgent] Validating PO: {po.po_number}")

        self.active_tasks[task_id] = task
        task.status = SubAgentStatus.RUNNING

        try:
            # Execute validation
            result = validate_purchase_order(po)

            task.status = SubAgentStatus.COMPLETED
            task.result = {
                "validation_result": result.model_dump() if hasattr(result, 'model_dump') else result.dict(),
                "is_valid": result.is_valid,
                "error_count": len([i for i in result.issues if i.severity == ValidationSeverity.ERROR]),
                "warning_count": len([i for i in result.issues if i.severity == ValidationSeverity.WARNING]),
            }
            task.completed_at = datetime.now()

            logger.info(
                f"[SubAgent] Validation completed for {po.po_number}: "
                f"valid={result.is_valid}, issues={len(result.issues)}"
            )

        except Exception as e:
            task.status = SubAgentStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"[SubAgent] Validation failed for {po.po_number}: {e}")

        # Move to completed tasks
        del self.active_tasks[task_id]
        self.completed_tasks.append(task)

        return task

    def spawn_batch_validators(
        self,
        purchase_orders: List[PurchaseOrder]
    ) -> List[SubAgentTask]:
        """Spawn validators for multiple purchase orders.

        Args:
            purchase_orders: List of purchase orders to validate

        Returns:
            List of SubAgentTask objects
        """
        tasks = []

        for po in purchase_orders:
            if self.should_spawn_validator(po):
                task = self.spawn_validator(po)
                tasks.append(task)
            else:
                logger.debug(f"Skipping validation for low-risk PO: {po.po_number}")

        logger.info(f"[SubAgent] Batch validation complete: {len(tasks)} POs validated")

        return tasks

    def get_validation_summary(
        self,
        tasks: List[SubAgentTask]
    ) -> Dict[str, Any]:
        """Get summary of validation results.

        Args:
            tasks: List of completed validation tasks

        Returns:
            Summary dictionary
        """
        total = len(tasks)
        passed = 0
        failed = 0
        errors = 0
        total_issues = 0

        for task in tasks:
            if task.status == SubAgentStatus.FAILED:
                errors += 1
            elif task.result:
                if task.result.get("is_valid", False):
                    passed += 1
                else:
                    failed += 1
                total_issues += (
                    task.result.get("error_count", 0) +
                    task.result.get("warning_count", 0)
                )

        return {
            "total_validated": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_issues": total_issues,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0
        }

    def format_validation_report(
        self,
        tasks: List[SubAgentTask]
    ) -> str:
        """Format validation results as a readable report.

        Args:
            tasks: List of completed validation tasks

        Returns:
            Formatted report string
        """
        lines = ["", "=== Validation Report ===", ""]

        summary = self.get_validation_summary(tasks)
        lines.append(f"Total POs Validated: {summary['total_validated']}")
        lines.append(f"Passed: {summary['passed']} | Failed: {summary['failed']} | Errors: {summary['errors']}")
        lines.append(f"Pass Rate: {summary['pass_rate']}%")
        lines.append("")

        for task in tasks:
            po_number = task.input_data.get("po_number", "Unknown")
            lines.append(f"--- {po_number} ---")

            if task.status == SubAgentStatus.FAILED:
                lines.append(f"  Status: FAILED - {task.error}")
            elif task.result:
                is_valid = task.result.get("is_valid", False)
                status = "PASSED" if is_valid else "FAILED"
                lines.append(f"  Status: {status}")

                error_count = task.result.get("error_count", 0)
                warning_count = task.result.get("warning_count", 0)

                if error_count > 0 or warning_count > 0:
                    lines.append(f"  Issues: {error_count} errors, {warning_count} warnings")

            lines.append("")

        lines.append("=== End Report ===")

        return "\n".join(lines)


# Global spawner instance
_validator_spawner: Optional[ValidatorSpawner] = None


def get_validator_spawner() -> ValidatorSpawner:
    """Get the global validator spawner instance.

    Returns:
        ValidatorSpawner instance
    """
    global _validator_spawner
    if _validator_spawner is None:
        _validator_spawner = ValidatorSpawner()
    return _validator_spawner


def validate_po_with_subagent(
    po: PurchaseOrder,
    force_validation: bool = False
) -> Optional[SubAgentTask]:
    """Validate a PO using sub-agent if needed.

    Args:
        po: Purchase order to validate
        force_validation: Force validation even for low-risk POs

    Returns:
        SubAgentTask if validation was performed, None otherwise
    """
    spawner = get_validator_spawner()

    if force_validation or spawner.should_spawn_validator(po):
        return spawner.spawn_validator(po)

    return None
