"""Base state classes for all agents.

This module provides base state classes and utilities that can be
reused across different agent implementations.
"""

from typing import List, Dict, Any, TypedDict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WorkflowStage(str, Enum):
    """Standard workflow stages for agents."""
    INITIAL = "initial"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETE = "complete"
    ERROR = "error"


class HITLGateType(str, Enum):
    """Types of Human-in-the-Loop approval gates."""
    PO_CREATION = "po_creation"
    SUPPLIER_SELECTION = "supplier_selection"
    HIGH_VALUE_APPROVAL = "high_value_approval"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"
    EXCEPTION_HANDLING = "exception_handling"


class BaseAgentState(TypedDict):
    """Base state that all agent states should include.

    Attributes:
        workflow_stage: Current stage in the workflow
        errors: List of any errors encountered
        metadata: Additional metadata for the workflow
    """
    workflow_stage: str
    errors: List[str]
    metadata: Dict[str, Any]


class HITLRequest(BaseModel):
    """Request for human-in-the-loop approval.

    Attributes:
        gate_type: Type of HITL gate
        request_id: Unique identifier for this request
        title: Short title for the approval request
        description: Detailed description of what needs approval
        options: Available response options
        data: Additional data relevant to the decision
        created_at: When the request was created
        expires_at: Optional expiration time
    """
    gate_type: HITLGateType = Field(..., description="Type of approval gate")
    request_id: str = Field(..., description="Unique request identifier")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    options: List[str] = Field(default_factory=lambda: ["approve", "reject"])
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None)


class HITLResponse(BaseModel):
    """Response to a human-in-the-loop approval request.

    Attributes:
        request_id: ID of the original request
        decision: The decision made (e.g., 'approve', 'reject')
        reason: Optional reason for the decision
        modified_data: Any modifications to the original data
        responded_at: When the response was given
    """
    request_id: str = Field(..., description="Original request ID")
    decision: str = Field(..., description="Decision made")
    reason: Optional[str] = Field(default=None, description="Reason for decision")
    modified_data: Optional[Dict[str, Any]] = Field(default=None)
    responded_at: datetime = Field(default_factory=datetime.now)


class AgentMessage(BaseModel):
    """Message passed between agents.

    Attributes:
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        message_type: Type of message (request, response, notification)
        content: Message content
        correlation_id: ID to correlate requests and responses
        timestamp: When the message was created
    """
    sender: str = Field(..., description="Sender agent ID")
    recipient: str = Field(..., description="Recipient agent ID")
    message_type: str = Field(..., description="Message type")
    content: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.now)


class WorkflowContext(BaseModel):
    """Context information for workflow execution.

    Attributes:
        session_id: Unique session identifier
        user_id: Optional user identifier
        started_at: When the workflow started
        current_step: Current step in the workflow
        total_steps: Total number of steps
        task_breakdown: Optional list of planned tasks
    """
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    started_at: datetime = Field(default_factory=datetime.now)
    current_step: int = Field(default=0, description="Current step number")
    total_steps: int = Field(default=0, description="Total steps")
    task_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


def create_initial_state(state_class: type, **kwargs) -> Dict[str, Any]:
    """Create an initial state with default values.

    Args:
        state_class: TypedDict class to create state for
        **kwargs: Override values for specific fields

    Returns:
        Dictionary with initial state values
    """
    # Get annotations from the state class
    annotations = getattr(state_class, '__annotations__', {})

    # Default values for common types
    defaults = {
        str: "",
        int: 0,
        float: 0.0,
        bool: False,
        list: [],
        dict: {},
        List: [],
        Dict: {},
    }

    # Build initial state
    state = {}
    for field_name, field_type in annotations.items():
        if field_name in kwargs:
            state[field_name] = kwargs[field_name]
        else:
            # Get origin type for generic types
            origin = getattr(field_type, '__origin__', field_type)
            if origin in defaults:
                state[field_name] = defaults[origin].copy() if isinstance(defaults[origin], (list, dict)) else defaults[origin]
            else:
                state[field_name] = None

    return state
