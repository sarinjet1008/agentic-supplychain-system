"""Common reusable node functions for agents.

This module provides utility functions that can be used as nodes
across different agent workflows.
"""

import logging
import uuid
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from functools import wraps

from agent.base.state_base import (
    WorkflowStage,
    HITLGateType,
    HITLRequest,
    HITLResponse,
)

logger = logging.getLogger(__name__)


def log_node_execution(func: Callable) -> Callable:
    """Decorator to log node execution with timing.

    Args:
        func: Node function to wrap

    Returns:
        Wrapped function with logging
    """
    @wraps(func)
    def wrapper(state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        node_name = func.__name__
        start_time = datetime.now()

        logger.info(f"[Node] Starting: {node_name}")

        try:
            result = func(state, *args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[Node] Completed: {node_name} ({duration:.2f}s)")
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"[Node] Failed: {node_name} ({duration:.2f}s) - {e}")
            raise

    return wrapper


def create_error_response(
    state: Dict[str, Any],
    error_message: str,
    error_code: Optional[str] = None
) -> Dict[str, Any]:
    """Create an error response state update.

    Args:
        state: Current state
        error_message: Error message to include
        error_code: Optional error code

    Returns:
        State update with error information
    """
    errors = state.get("errors", []).copy()
    errors.append(f"[{error_code or 'ERROR'}] {error_message}")

    return {
        "workflow_stage": WorkflowStage.ERROR.value,
        "errors": errors,
        "agent_response": f"An error occurred: {error_message}"
    }


def create_hitl_request(
    gate_type: HITLGateType,
    title: str,
    description: str,
    options: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None
) -> HITLRequest:
    """Create a HITL approval request.

    Args:
        gate_type: Type of approval gate
        title: Short title for the request
        description: Detailed description
        options: Available response options
        data: Additional context data

    Returns:
        HITLRequest object
    """
    return HITLRequest(
        gate_type=gate_type,
        request_id=str(uuid.uuid4())[:8],
        title=title,
        description=description,
        options=options or ["approve", "reject"],
        data=data or {}
    )


def check_approval_response(
    user_message: str,
    positive_keywords: Optional[List[str]] = None,
    negative_keywords: Optional[List[str]] = None
) -> Optional[bool]:
    """Check user message for approval/rejection response.

    Args:
        user_message: User's input message
        positive_keywords: Words indicating approval
        negative_keywords: Words indicating rejection

    Returns:
        True for approval, False for rejection, None if unclear
    """
    message_lower = user_message.lower().strip()

    positive = positive_keywords or [
        "yes", "y", "approve", "ok", "okay", "sure", "proceed",
        "go ahead", "confirm", "agreed", "accept"
    ]
    negative = negative_keywords or [
        "no", "n", "reject", "cancel", "stop", "decline",
        "deny", "refuse", "abort"
    ]

    if any(keyword in message_lower for keyword in positive):
        return True
    if any(keyword in message_lower for keyword in negative):
        return False

    return None


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a number as currency.

    Args:
        amount: Amount to format
        currency: Currency code

    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def format_list_response(
    items: List[Dict[str, Any]],
    title: str,
    item_formatter: Callable[[Dict[str, Any]], str]
) -> str:
    """Format a list of items for display.

    Args:
        items: List of items to display
        title: Title for the list
        item_formatter: Function to format each item

    Returns:
        Formatted string
    """
    if not items:
        return f"{title}: No items found."

    lines = [title]
    for i, item in enumerate(items, 1):
        lines.append(f"  {i}. {item_formatter(item)}")

    return "\n".join(lines)


def merge_state_updates(*updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple state updates into one.

    Later updates override earlier ones for the same key.

    Args:
        *updates: State update dictionaries

    Returns:
        Merged state update
    """
    result = {}
    for update in updates:
        if update:
            result.update(update)
    return result


def validate_required_fields(
    state: Dict[str, Any],
    required_fields: List[str]
) -> Optional[str]:
    """Validate that required fields are present in state.

    Args:
        state: Current state
        required_fields: List of required field names

    Returns:
        Error message if validation fails, None otherwise
    """
    missing = []
    for field in required_fields:
        if field not in state or state[field] is None:
            missing.append(field)

    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


def extract_items_from_state(
    state: Dict[str, Any],
    items_key: str,
    item_id_field: str = "id"
) -> Dict[str, Any]:
    """Extract items from state into a lookup dictionary.

    Args:
        state: Current state
        items_key: Key containing the list of items
        item_id_field: Field name for item IDs

    Returns:
        Dictionary mapping item IDs to items
    """
    items = state.get(items_key, [])
    return {item.get(item_id_field): item for item in items if item.get(item_id_field)}


class NodeChain:
    """Chain multiple node functions together.

    Useful for creating composite nodes from smaller functions.
    """

    def __init__(self, name: str = "chain"):
        """Initialize the node chain.

        Args:
            name: Name for logging purposes
        """
        self.name = name
        self.nodes: List[Callable] = []

    def add(self, node: Callable) -> "NodeChain":
        """Add a node function to the chain.

        Args:
            node: Node function to add

        Returns:
            Self for chaining
        """
        self.nodes.append(node)
        return self

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all nodes in the chain.

        Args:
            state: Initial state

        Returns:
            Final state after all nodes
        """
        logger.info(f"[NodeChain] Executing {self.name} with {len(self.nodes)} nodes")

        current_state = state.copy()
        for i, node in enumerate(self.nodes):
            node_name = getattr(node, '__name__', f'node_{i}')
            logger.debug(f"[NodeChain] Running node {i+1}/{len(self.nodes)}: {node_name}")

            result = node(current_state)
            current_state.update(result)

            # Check for errors and abort if needed
            if current_state.get("workflow_stage") == WorkflowStage.ERROR.value:
                logger.warning(f"[NodeChain] Aborted due to error in {node_name}")
                break

        return current_state
