"""A2A Server - Server for receiving Agent-to-Agent requests.

This module provides a server for receiving and handling A2A requests,
exposing agent capabilities to other agents.
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from protocols.a2a.message_schemas import (
    A2ARequest,
    A2AResponse,
    A2AError,
    create_response,
    create_error_response,
)

logger = logging.getLogger(__name__)


class HandlerStatus(str, Enum):
    """Status of a request handler."""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


@dataclass
class RequestHandler:
    """Handler for A2A requests.

    Attributes:
        method: Method name this handler responds to
        handler: Callable that processes the request
        description: Description of the handler
        input_schema: JSON Schema for input validation
        output_schema: JSON Schema for output
        status: Handler status
        call_count: Number of times called
    """
    method: str
    handler: Callable
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    status: HandlerStatus = HandlerStatus.ACTIVE
    call_count: int = 0


class A2AServer:
    """Server for receiving A2A requests.

    The A2A server exposes agent capabilities to other agents through
    registered request handlers. It handles request validation, execution,
    and response formatting.

    Attributes:
        agent_id: ID of the agent running this server
        agent_name: Human-readable agent name
        handlers: Registered request handlers
        request_log: Log of received requests
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        version: str = "1.0.0"
    ):
        """Initialize the A2A server.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            version: Server version
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.version = version
        self.handlers: Dict[str, RequestHandler] = {}
        self.request_log: List[Dict[str, Any]] = []
        self._started_at = datetime.now()

        logger.info(f"A2A Server initialized: {agent_name} ({agent_id})")

    def register_handler(
        self,
        method: str,
        handler: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a request handler.

        Args:
            method: Method name to handle
            handler: Callable that processes requests
            description: Handler description
            input_schema: Optional input JSON Schema
            output_schema: Optional output JSON Schema
        """
        if method in self.handlers:
            logger.warning(f"Handler for '{method}' already registered, replacing")

        self.handlers[method] = RequestHandler(
            method=method,
            handler=handler,
            description=description,
            input_schema=input_schema or {},
            output_schema=output_schema or {}
        )

        logger.info(f"Registered handler: {method}")

    def unregister_handler(self, method: str) -> bool:
        """Unregister a request handler.

        Args:
            method: Method name to unregister

        Returns:
            True if handler was removed, False if not found
        """
        if method in self.handlers:
            del self.handlers[method]
            logger.info(f"Unregistered handler: {method}")
            return True
        return False

    def handle_request(self, request: A2ARequest) -> A2AResponse:
        """Handle an incoming A2A request.

        Args:
            request: The A2A request to handle

        Returns:
            A2A response
        """
        start_time = datetime.now()
        logger.info(
            f"[A2A Server:{self.agent_id}] Handling request: {request.method} "
            f"(ID: {request.id})"
        )

        # Find handler
        handler_info = self.handlers.get(request.method)
        if not handler_info:
            logger.warning(f"No handler for method: {request.method}")
            response = create_error_response(
                request.id,
                A2AError.METHOD_NOT_FOUND,
                f"Method not found: {request.method}",
                data={"available_methods": list(self.handlers.keys())}
            )
            self._log_request(request, response, start_time)
            return response

        # Check handler status
        if handler_info.status != HandlerStatus.ACTIVE:
            logger.warning(f"Handler {request.method} is {handler_info.status.value}")
            if handler_info.status == HandlerStatus.DISABLED:
                response = create_error_response(
                    request.id,
                    A2AError.METHOD_NOT_FOUND,
                    f"Method is disabled: {request.method}"
                )
                self._log_request(request, response, start_time)
                return response

        # Execute handler
        try:
            handler_info.call_count += 1
            result = handler_info.handler(request.params)

            response = create_response(
                request.id,
                result,
                source_agent=self.agent_id
            )

            logger.info(
                f"[A2A Server:{self.agent_id}] Request {request.id} handled successfully"
            )

        except Exception as e:
            logger.error(
                f"[A2A Server:{self.agent_id}] Handler error: {e}",
                exc_info=True
            )
            response = create_error_response(
                request.id,
                A2AError.INTERNAL_ERROR,
                f"Handler error: {str(e)}"
            )

        self._log_request(request, response, start_time)
        return response

    def _log_request(
        self,
        request: A2ARequest,
        response: A2AResponse,
        start_time: datetime
    ) -> None:
        """Log a request/response pair.

        Args:
            request: The received request
            response: The sent response
            start_time: When request handling started
        """
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        self.request_log.append({
            "request_id": request.id,
            "method": request.method,
            "source_agent": request.source_agent,
            "timestamp": start_time.isoformat(),
            "duration_ms": round(duration_ms, 2),
            "success": response.error is None,
            "error_code": response.error.get("code") if response.error else None
        })

        # Keep log manageable
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-500:]

    def get_capabilities(self) -> List[str]:
        """Get list of supported methods/capabilities.

        Returns:
            List of method names
        """
        return [
            method for method, handler in self.handlers.items()
            if handler.status == HandlerStatus.ACTIVE
        ]

    def get_handler_info(self, method: str) -> Optional[Dict[str, Any]]:
        """Get information about a handler.

        Args:
            method: Method name

        Returns:
            Handler information or None
        """
        handler = self.handlers.get(method)
        if not handler:
            return None

        return {
            "method": handler.method,
            "description": handler.description,
            "status": handler.status.value,
            "input_schema": handler.input_schema,
            "output_schema": handler.output_schema,
            "call_count": handler.call_count
        }

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information.

        Returns:
            Server information dictionary
        """
        uptime = (datetime.now() - self._started_at).total_seconds()

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "capabilities": self.get_capabilities(),
            "total_handlers": len(self.handlers),
            "active_handlers": len([
                h for h in self.handlers.values()
                if h.status == HandlerStatus.ACTIVE
            ])
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get server statistics.

        Returns:
            Statistics dictionary
        """
        total_requests = len(self.request_log)
        successful = len([r for r in self.request_log if r["success"]])
        failed = total_requests - successful

        avg_duration = 0
        if self.request_log:
            avg_duration = sum(r["duration_ms"] for r in self.request_log) / total_requests

        return {
            "agent_id": self.agent_id,
            "total_requests": total_requests,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total_requests * 100, 1) if total_requests > 0 else 0,
            "avg_duration_ms": round(avg_duration, 2),
            "handler_calls": {
                method: handler.call_count
                for method, handler in self.handlers.items()
            }
        }

    def get_recent_requests(
        self,
        limit: int = 20,
        method: Optional[str] = None,
        errors_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get recent request log entries.

        Args:
            limit: Maximum entries to return
            method: Optional filter by method
            errors_only: Only return failed requests

        Returns:
            List of log entries
        """
        log = self.request_log

        if method:
            log = [r for r in log if r["method"] == method]

        if errors_only:
            log = [r for r in log if not r["success"]]

        return log[-limit:]


def create_agent_server(
    agent_id: str,
    agent_name: str,
    workflow: Any
) -> A2AServer:
    """Create an A2A server for an agent with workflow integration.

    Args:
        agent_id: Agent identifier
        agent_name: Human-readable name
        workflow: Compiled LangGraph workflow

    Returns:
        Configured A2AServer
    """
    server = A2AServer(agent_id, agent_name)

    # Register workflow invoke as the main handler
    def invoke_handler(params: Dict[str, Any]) -> Dict[str, Any]:
        return workflow.invoke(params)

    server.register_handler(
        method="invoke",
        handler=invoke_handler,
        description=f"Invoke the {agent_name} workflow"
    )

    return server
