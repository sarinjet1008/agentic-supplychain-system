"""Base Agent Adapter - Abstract base class for A2A agent adapters.

This module provides the base class for agent adapters that wrap
agent workflows for A2A protocol communication.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

from protocols.a2a.message_schemas import A2ARequest, A2AResponse, A2AError
from protocols.a2a.server import A2AServer
from protocols.a2a.client import A2AClient
from protocols.a2a.agent_cards import AgentCard

logger = logging.getLogger(__name__)


@dataclass
class AdapterConfig:
    """Configuration for an agent adapter.

    Attributes:
        agent_id: Unique agent identifier
        agent_name: Human-readable agent name
        version: Adapter version
        timeout_seconds: Request timeout
        enable_logging: Whether to log requests
        custom_settings: Additional custom settings
    """
    agent_id: str
    agent_name: str
    version: str = "1.0.0"
    timeout_seconds: float = 30.0
    enable_logging: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)


class BaseAgentAdapter(ABC):
    """Base class for agent adapters.

    Agent adapters wrap agent workflows to expose them through the A2A protocol.
    They handle message translation, state management, and error handling.

    Subclasses must implement:
    - _register_handlers(): Register method handlers with the server
    - get_agent_card(): Return the agent's capability card

    Attributes:
        config: Adapter configuration
        workflow: The agent's workflow (if applicable)
        server: A2A server for receiving requests
        client: A2A client for sending requests
    """

    def __init__(
        self,
        config: AdapterConfig,
        workflow: Optional[Any] = None,
        router: Optional[Any] = None
    ):
        """Initialize the adapter.

        Args:
            config: Adapter configuration
            workflow: Optional compiled workflow
            router: Optional A2A router for client
        """
        self.config = config
        self.workflow = workflow

        # Create server and client
        self.server = A2AServer(
            agent_id=config.agent_id,
            agent_name=config.agent_name,
            version=config.version
        )

        self.client = A2AClient(
            source_agent=config.agent_id,
            router=router
        )

        # Register handlers
        self._register_handlers()

        logger.info(
            f"Adapter initialized for {config.agent_name} ({config.agent_id})"
        )

    @abstractmethod
    def _register_handlers(self) -> None:
        """Register method handlers with the server.

        Subclasses must implement this to register their specific handlers.
        """
        pass

    @abstractmethod
    def get_agent_card(self) -> AgentCard:
        """Get the agent's capability card.

        Returns:
            AgentCard defining agent capabilities
        """
        pass

    def handle_request(self, request: A2ARequest) -> A2AResponse:
        """Handle an incoming A2A request.

        Args:
            request: The A2A request

        Returns:
            A2A response
        """
        if self.config.enable_logging:
            logger.info(
                f"[{self.config.agent_id}] Handling request: {request.method}"
            )

        return self.server.handle_request(request)

    def send_request(
        self,
        method: str,
        params: Dict[str, Any],
        target_agent: Optional[str] = None
    ) -> A2AResponse:
        """Send a request to another agent.

        Args:
            method: Method to invoke
            params: Method parameters
            target_agent: Optional target agent ID

        Returns:
            A2A response
        """
        return self.client.send_request(method, params, target_agent)

    def invoke_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the agent's workflow.

        Args:
            state: Initial workflow state

        Returns:
            Final workflow state
        """
        if self.workflow is None:
            raise RuntimeError(f"No workflow configured for {self.config.agent_id}")

        return self.workflow.invoke(state)

    def get_capabilities(self) -> List[str]:
        """Get list of supported capabilities.

        Returns:
            List of capability names
        """
        return self.server.get_capabilities()

    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics.

        Returns:
            Combined server and client statistics
        """
        return {
            "agent_id": self.config.agent_id,
            "server": self.server.get_statistics(),
            "client": self.client.get_statistics()
        }

    def set_router(self, router: Any) -> None:
        """Set the A2A router for the client.

        Args:
            router: A2A router instance
        """
        self.client.set_router(router)


class WorkflowAdapter(BaseAgentAdapter):
    """Adapter that wraps a complete workflow.

    This adapter automatically creates a handler that invokes
    the workflow when receiving requests.
    """

    def __init__(
        self,
        config: AdapterConfig,
        workflow: Any,
        router: Optional[Any] = None,
        method_name: str = "invoke"
    ):
        """Initialize the workflow adapter.

        Args:
            config: Adapter configuration
            workflow: Compiled workflow to wrap
            router: Optional A2A router
            method_name: Name for the invoke method
        """
        self.method_name = method_name
        super().__init__(config, workflow, router)

    def _register_handlers(self) -> None:
        """Register the workflow invoke handler."""
        self.server.register_handler(
            method=self.method_name,
            handler=self._workflow_handler,
            description=f"Invoke the {self.config.agent_name} workflow"
        )

    def _workflow_handler(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler that invokes the workflow.

        Args:
            params: Workflow input parameters

        Returns:
            Workflow result
        """
        return self.invoke_workflow(params)

    def get_agent_card(self) -> AgentCard:
        """Get a basic agent card.

        Returns:
            AgentCard with invoke capability
        """
        from protocols.a2a.agent_cards import create_agent_card
        return create_agent_card(
            agent_id=self.config.agent_id,
            name=self.config.agent_name,
            capabilities=[self.method_name],
            version=self.config.version
        )
