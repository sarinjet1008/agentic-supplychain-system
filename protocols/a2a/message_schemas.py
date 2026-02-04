"""A2A Message Schemas for Agent-to-Agent Communication.

This module defines the message format for inter-agent communication following
a JSON-RPC 2.0 style protocol.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, ClassVar
from datetime import datetime
import uuid


class A2ARequest(BaseModel):
    """Agent-to-Agent request message.

    Attributes:
        jsonrpc: JSON-RPC version (always "2.0")
        method: The capability/method to invoke (e.g., "check_inventory")
        params: Parameters for the method call
        id: Unique request identifier
        source_agent: ID of the agent making the request
        target_agent: ID of the agent to handle the request
        timestamp: When the request was created
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method/capability to invoke")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Request ID")
    source_agent: Optional[str] = Field(default=None, description="Source agent ID")
    target_agent: Optional[str] = Field(default=None, description="Target agent ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Request timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "method": "check_inventory",
                "params": {"check_all": True},
                "id": "req-123-456",
                "source_agent": "orchestrator",
                "target_agent": "inventory_monitor",
                "timestamp": "2026-01-29T10:30:00Z"
            }
        }


class A2AResponse(BaseModel):
    """Agent-to-Agent response message.

    Attributes:
        jsonrpc: JSON-RPC version (always "2.0")
        result: Successful result data (mutually exclusive with error)
        error: Error information (mutually exclusive with result)
        id: Request ID this response corresponds to
        source_agent: ID of the agent sending the response
        timestamp: When the response was created
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Success result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")
    id: str = Field(..., description="Request ID")
    source_agent: Optional[str] = Field(default=None, description="Source agent ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "jsonrpc": "2.0",
                "result": {
                    "low_stock_items": [{"item_id": "101", "quantity": 5}]
                },
                "id": "req-123-456",
                "source_agent": "inventory_monitor",
                "timestamp": "2026-01-29T10:30:05Z"
            }
        }


class A2AError(BaseModel):
    """Standard error format for A2A responses.

    Attributes:
        code: Error code (following JSON-RPC conventions)
        message: Human-readable error message
        data: Additional error details
    """
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional error data")

    # Standard JSON-RPC error codes
    PARSE_ERROR: ClassVar[int] = -32700
    INVALID_REQUEST: ClassVar[int] = -32600
    METHOD_NOT_FOUND: ClassVar[int] = -32601
    INVALID_PARAMS: ClassVar[int] = -32602
    INTERNAL_ERROR: ClassVar[int] = -32603

    # Custom application error codes
    AGENT_NOT_FOUND: ClassVar[int] = -32001
    AGENT_UNAVAILABLE: ClassVar[int] = -32002
    TIMEOUT: ClassVar[int] = -32003
    VALIDATION_ERROR: ClassVar[int] = -32004


def create_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    source_agent: Optional[str] = None,
    target_agent: Optional[str] = None,
    request_id: Optional[str] = None
) -> A2ARequest:
    """Create an A2A request message.

    Args:
        method: The capability/method to invoke
        params: Parameters for the method call
        source_agent: ID of the agent making the request
        target_agent: ID of the agent to handle the request
        request_id: Optional custom request ID

    Returns:
        A2ARequest instance
    """
    return A2ARequest(
        method=method,
        params=params or {},
        source_agent=source_agent,
        target_agent=target_agent,
        id=request_id or str(uuid.uuid4())
    )


def create_response(
    request_id: str,
    result: Dict[str, Any],
    source_agent: Optional[str] = None
) -> A2AResponse:
    """Create a successful A2A response message.

    Args:
        request_id: The ID of the request being responded to
        result: The result data
        source_agent: ID of the agent sending the response

    Returns:
        A2AResponse instance
    """
    return A2AResponse(
        id=request_id,
        result=result,
        source_agent=source_agent
    )


def create_error_response(
    request_id: str,
    code: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    source_agent: Optional[str] = None
) -> A2AResponse:
    """Create an error A2A response message.

    Args:
        request_id: The ID of the request being responded to
        code: Error code
        message: Error message
        data: Additional error data
        source_agent: ID of the agent sending the response

    Returns:
        A2AResponse instance with error
    """
    error = A2AError(code=code, message=message, data=data)
    return A2AResponse(
        id=request_id,
        error=error.model_dump(),
        source_agent=source_agent
    )
