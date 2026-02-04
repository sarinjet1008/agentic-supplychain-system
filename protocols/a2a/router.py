"""A2A Router for Agent-to-Agent Communication.

This module provides routing functionality to direct A2A messages to the appropriate
agents based on their capabilities as defined in agent cards.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from protocols.a2a.message_schemas import A2ARequest, A2AResponse, A2AError

logger = logging.getLogger(__name__)


class A2ARouter:
    """Routes A2A messages to appropriate agents based on agent cards.

    The router loads agent capability definitions from JSON agent cards and
    maintains a registry of agent workflow executors. When a request is received,
    it finds the appropriate agent based on the requested capability and invokes
    the agent's workflow.

    Attributes:
        agent_cards: Dictionary of agent_id -> agent card data
        agent_workflows: Dictionary of agent_id -> workflow executor function
    """

    def __init__(self, agent_cards_dir: Optional[str] = None):
        """Initialize the A2A router.

        Args:
            agent_cards_dir: Directory containing agent card JSON files.
                            Defaults to config/agent_cards/
        """
        if agent_cards_dir is None:
            agent_cards_dir = Path(__file__).parent.parent.parent / "config" / "agent_cards"
        else:
            agent_cards_dir = Path(agent_cards_dir)

        self.agent_cards_dir = agent_cards_dir
        self.agent_cards: Dict[str, Dict[str, Any]] = {}
        self.agent_workflows: Dict[str, Callable] = {}

        self._load_agent_cards()
        logger.info(f"A2A Router initialized with {len(self.agent_cards)} agent cards")

    def _load_agent_cards(self) -> None:
        """Load all agent cards from the agent_cards directory."""
        if not self.agent_cards_dir.exists():
            logger.warning(f"Agent cards directory not found: {self.agent_cards_dir}")
            return

        for card_file in self.agent_cards_dir.glob("*.json"):
            try:
                with open(card_file, 'r') as f:
                    card_data = json.load(f)
                    agent_id = card_data.get("agent_id")
                    if agent_id:
                        self.agent_cards[agent_id] = card_data
                        logger.info(f"Loaded agent card: {agent_id} ({card_data.get('name', 'Unknown')})")
                    else:
                        logger.warning(f"Agent card missing agent_id: {card_file}")
            except Exception as e:
                logger.error(f"Failed to load agent card {card_file}: {e}")

    def register_agent(self, agent_id: str, workflow: Callable) -> None:
        """Register an agent workflow executor.

        Args:
            agent_id: The agent's unique identifier (must match an agent card)
            workflow: Callable that executes the agent's workflow (typically workflow.invoke)
        """
        if agent_id not in self.agent_cards:
            logger.warning(f"Registering agent {agent_id} without a corresponding agent card")

        self.agent_workflows[agent_id] = workflow
        logger.info(f"Registered workflow for agent: {agent_id}")

    def find_agent_by_capability(self, method: str) -> Optional[str]:
        """Find an agent that supports the given capability/method.

        Args:
            method: The capability/method name to search for

        Returns:
            The agent_id of a capable agent, or None if not found
        """
        for agent_id, card in self.agent_cards.items():
            capabilities = card.get("capabilities", [])
            if method in capabilities:
                logger.debug(f"Found agent {agent_id} for capability: {method}")
                return agent_id

        logger.warning(f"No agent found for capability: {method}")
        return None

    def find_agent_by_id(self, agent_id: str) -> Optional[str]:
        """Find an agent by its ID.

        Args:
            agent_id: The agent's unique identifier

        Returns:
            The agent_id if found, None otherwise
        """
        if agent_id in self.agent_cards:
            return agent_id
        logger.warning(f"Agent not found: {agent_id}")
        return None

    def route_message(self, request: A2ARequest) -> A2AResponse:
        """Route an A2A request to the appropriate agent.

        Args:
            request: The A2A request message

        Returns:
            A2A response with either result or error
        """
        logger.info(f"[A2A Router] Routing message: {request.method} (ID: {request.id})")

        # Find target agent
        target_agent_id = None
        if request.target_agent:
            # Explicit target specified
            target_agent_id = self.find_agent_by_id(request.target_agent)
            if not target_agent_id:
                return self._create_error_response(
                    request.id,
                    A2AError.AGENT_NOT_FOUND,
                    f"Target agent not found: {request.target_agent}"
                )
        else:
            # Find agent by capability
            target_agent_id = self.find_agent_by_capability(request.method)
            if not target_agent_id:
                return self._create_error_response(
                    request.id,
                    A2AError.METHOD_NOT_FOUND,
                    f"No agent supports capability: {request.method}"
                )

        # Check if workflow is registered
        workflow = self.agent_workflows.get(target_agent_id)
        if not workflow:
            return self._create_error_response(
                request.id,
                A2AError.AGENT_UNAVAILABLE,
                f"Agent workflow not registered: {target_agent_id}"
            )

        # Execute workflow
        try:
            logger.info(f"[A2A Router] Invoking agent: {target_agent_id}")
            result = workflow.invoke(request.params)

            logger.info(f"[A2A Router] Agent {target_agent_id} completed successfully")
            return A2AResponse(
                id=request.id,
                result=result,
                source_agent=target_agent_id
            )
        except Exception as e:
            logger.error(f"[A2A Router] Agent {target_agent_id} failed: {e}", exc_info=True)
            return self._create_error_response(
                request.id,
                A2AError.INTERNAL_ERROR,
                f"Agent execution failed: {str(e)}",
                data={"agent_id": target_agent_id, "error_type": type(e).__name__}
            )

    def _create_error_response(
        self,
        request_id: str,
        error_code: int,
        error_message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> A2AResponse:
        """Create an error response.

        Args:
            request_id: The request ID
            error_code: Error code
            error_message: Error message
            data: Optional additional error data

        Returns:
            A2A response with error
        """
        error = A2AError(code=error_code, message=error_message, data=data)
        return A2AResponse(
            id=request_id,
            error=error.model_dump(),
            source_agent="router"
        )

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent card information.

        Args:
            agent_id: The agent's unique identifier

        Returns:
            Agent card data or None if not found
        """
        return self.agent_cards.get(agent_id)

    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """List all registered agents and their capabilities.

        Returns:
            Dictionary of agent_id -> agent summary
        """
        agent_list = {}
        for agent_id, card in self.agent_cards.items():
            agent_list[agent_id] = {
                "name": card.get("name", "Unknown"),
                "description": card.get("description", ""),
                "capabilities": card.get("capabilities", []),
                "has_workflow": agent_id in self.agent_workflows
            }
        return agent_list
