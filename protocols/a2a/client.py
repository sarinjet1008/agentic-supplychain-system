"""A2A Client - Client for sending Agent-to-Agent requests.

This module provides a client for sending A2A requests to other agents,
handling serialization, timeouts, and error handling.
"""

import logging
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import asyncio

from protocols.a2a.message_schemas import (
    A2ARequest,
    A2AResponse,
    A2AError,
    create_request,
    create_error_response,
)

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Exception raised by A2A client operations."""

    def __init__(self, message: str, code: int = -32000, data: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.data = data or {}
        super().__init__(message)


class A2AClient:
    """Client for sending A2A requests to agents.

    The A2A client provides methods for sending requests to other agents
    using the Agent-to-Agent protocol. It handles request serialization,
    timeout management, and error handling.

    Attributes:
        source_agent: ID of the agent using this client
        router: Reference to the A2A router for message routing
        default_timeout: Default timeout for requests in seconds
        request_history: History of sent requests
    """

    def __init__(
        self,
        source_agent: str,
        router: Optional[Any] = None,
        default_timeout: float = 30.0
    ):
        """Initialize the A2A client.

        Args:
            source_agent: ID of the agent using this client
            router: Optional A2A router for message routing
            default_timeout: Default timeout for requests in seconds
        """
        self.source_agent = source_agent
        self.router = router
        self.default_timeout = default_timeout
        self.request_history: list = []
        self._pending_requests: Dict[str, A2ARequest] = {}

        logger.info(f"A2A Client initialized for agent: {source_agent}")

    def set_router(self, router: Any) -> None:
        """Set the A2A router for message routing.

        Args:
            router: A2A router instance
        """
        self.router = router
        logger.debug(f"Router set for client {self.source_agent}")

    def send_request(
        self,
        method: str,
        params: Dict[str, Any],
        target_agent: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> A2AResponse:
        """Send a request to another agent.

        Args:
            method: Method/capability to invoke
            params: Parameters for the method
            target_agent: Optional specific agent to target
            timeout: Optional timeout override

        Returns:
            A2A response from the target agent

        Raises:
            A2AClientError: If request fails or times out
        """
        if self.router is None:
            raise A2AClientError(
                "No router configured",
                code=A2AError.INTERNAL_ERROR
            )

        # Create request
        request = create_request(
            method=method,
            params=params,
            source_agent=self.source_agent,
            target_agent=target_agent
        )

        logger.info(f"[A2A Client] Sending request: {method} (ID: {request.id})")
        if target_agent:
            logger.debug(f"[A2A Client] Target agent: {target_agent}")

        # Track pending request
        self._pending_requests[request.id] = request

        try:
            # Route the request
            response = self.router.route_message(request)

            # Log response
            if response.error:
                logger.warning(
                    f"[A2A Client] Request {request.id} failed: "
                    f"{response.error.get('message', 'Unknown error')}"
                )
            else:
                logger.info(f"[A2A Client] Request {request.id} completed successfully")

            # Record in history
            self._record_request(request, response)

            return response

        except Exception as e:
            logger.error(f"[A2A Client] Request {request.id} error: {e}")
            error_response = create_error_response(
                request.id,
                A2AError.INTERNAL_ERROR,
                str(e)
            )
            self._record_request(request, error_response)
            raise A2AClientError(str(e), code=A2AError.INTERNAL_ERROR)

        finally:
            # Remove from pending
            self._pending_requests.pop(request.id, None)

    def send_notification(
        self,
        method: str,
        params: Dict[str, Any],
        target_agent: Optional[str] = None
    ) -> None:
        """Send a notification (no response expected).

        Args:
            method: Method/capability to invoke
            params: Parameters for the method
            target_agent: Optional specific agent to target
        """
        if self.router is None:
            logger.warning("No router configured, notification not sent")
            return

        # Create notification (no ID, no response expected)
        request = A2ARequest(
            method=method,
            params=params,
            source_agent=self.source_agent,
            target_agent=target_agent
        )
        # Clear the ID to indicate notification
        request.id = ""

        logger.info(f"[A2A Client] Sending notification: {method}")

        try:
            # Route but don't expect response
            self.router.route_message(request)
        except Exception as e:
            logger.error(f"[A2A Client] Notification error: {e}")

    def _record_request(
        self,
        request: A2ARequest,
        response: A2AResponse
    ) -> None:
        """Record a request/response pair in history.

        Args:
            request: The sent request
            response: The received response
        """
        self.request_history.append({
            "request_id": request.id,
            "method": request.method,
            "target_agent": request.target_agent,
            "timestamp": datetime.now().isoformat(),
            "success": response.error is None,
            "error": response.error
        })

        # Keep history manageable
        if len(self.request_history) > 100:
            self.request_history = self.request_history[-50:]

    def get_pending_requests(self) -> Dict[str, A2ARequest]:
        """Get currently pending requests.

        Returns:
            Dictionary of request_id -> A2ARequest
        """
        return self._pending_requests.copy()

    def get_request_history(
        self,
        limit: int = 20,
        method: Optional[str] = None
    ) -> list:
        """Get request history.

        Args:
            limit: Maximum number of records to return
            method: Optional filter by method name

        Returns:
            List of history records
        """
        history = self.request_history

        if method:
            history = [h for h in history if h["method"] == method]

        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Statistics dictionary
        """
        total = len(self.request_history)
        successful = len([h for h in self.request_history if h["success"]])
        failed = total - successful

        return {
            "source_agent": self.source_agent,
            "total_requests": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 0,
            "pending_requests": len(self._pending_requests)
        }


class A2AClientPool:
    """Pool of A2A clients for multiple agents.

    Manages a pool of A2A clients, one per agent, sharing a common router.

    Attributes:
        router: Shared A2A router
        clients: Dictionary of agent_id -> A2AClient
    """

    def __init__(self, router: Any):
        """Initialize the client pool.

        Args:
            router: Shared A2A router
        """
        self.router = router
        self.clients: Dict[str, A2AClient] = {}

    def get_client(self, agent_id: str) -> A2AClient:
        """Get or create a client for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            A2AClient for the agent
        """
        if agent_id not in self.clients:
            self.clients[agent_id] = A2AClient(
                source_agent=agent_id,
                router=self.router
            )

        return self.clients[agent_id]

    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all clients.

        Returns:
            Statistics for all clients
        """
        return {
            agent_id: client.get_statistics()
            for agent_id, client in self.clients.items()
        }
