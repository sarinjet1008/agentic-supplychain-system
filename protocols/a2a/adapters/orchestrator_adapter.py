"""Orchestrator Adapter - A2A adapter for Orchestrator Agent.

This module provides an A2A adapter for the Orchestrator Agent,
exposing workflow coordination and user interaction capabilities.
"""

import logging
from typing import Dict, Any, Optional, List

from protocols.a2a.adapters.base_adapter import BaseAgentAdapter, AdapterConfig
from protocols.a2a.agent_cards import AgentCard, ORCHESTRATOR_CARD

logger = logging.getLogger(__name__)


class OrchestratorAdapter(BaseAgentAdapter):
    """A2A adapter for the Orchestrator Agent.

    The orchestrator adapter is special because it coordinates other agents.
    It exposes capabilities for parsing user input, coordinating workflows,
    and generating responses.

    Exposes the following capabilities:
    - parse_user_input: Parse and understand user messages
    - coordinate_workflow: Coordinate multi-agent workflow
    - generate_response: Generate response to user
    """

    def __init__(
        self,
        workflow: Optional[Any] = None,
        router: Optional[Any] = None
    ):
        """Initialize the orchestrator adapter.

        Args:
            workflow: Compiled orchestrator workflow
            router: A2A router for coordinating other agents
        """
        config = AdapterConfig(
            agent_id="orchestrator",
            agent_name="Orchestrator Agent",
            version="1.0.0"
        )
        self._sub_adapters: Dict[str, Any] = {}
        super().__init__(config, workflow, router)

    def _register_handlers(self) -> None:
        """Register orchestrator-specific handlers."""

        self.server.register_handler(
            method="parse_user_input",
            handler=self._parse_user_input,
            description="Parse and understand a user message",
            input_schema={
                "type": "object",
                "properties": {
                    "user_message": {
                        "type": "string",
                        "description": "User's input message"
                    },
                    "conversation_history": {
                        "type": "array",
                        "description": "Previous conversation messages"
                    }
                },
                "required": ["user_message"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "entities": {"type": "object"},
                    "workflow_stage": {"type": "string"}
                }
            }
        )

        self.server.register_handler(
            method="coordinate_workflow",
            handler=self._coordinate_workflow,
            description="Coordinate a multi-agent workflow",
            input_schema={
                "type": "object",
                "properties": {
                    "workflow_type": {
                        "type": "string",
                        "description": "Type of workflow to coordinate"
                    },
                    "initial_state": {
                        "type": "object",
                        "description": "Initial workflow state"
                    }
                },
                "required": ["workflow_type"]
            }
        )

        self.server.register_handler(
            method="generate_response",
            handler=self._generate_response,
            description="Generate a response to the user",
            input_schema={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "object",
                        "description": "Context for response generation"
                    },
                    "workflow_results": {
                        "type": "object",
                        "description": "Results from workflow execution"
                    }
                }
            }
        )

        self.server.register_handler(
            method="process_message",
            handler=self._process_message,
            description="Process a complete user message through the workflow",
            input_schema={
                "type": "object",
                "properties": {
                    "user_message": {"type": "string"},
                    "conversation_history": {"type": "array"},
                    "workflow_state": {"type": "object"}
                },
                "required": ["user_message"]
            }
        )

    def register_sub_adapter(self, agent_id: str, adapter: Any) -> None:
        """Register a sub-adapter for coordination.

        Args:
            agent_id: Agent identifier
            adapter: Agent adapter instance
        """
        self._sub_adapters[agent_id] = adapter
        logger.info(f"Registered sub-adapter: {agent_id}")

    def _parse_user_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Parse user input.

        Args:
            params: Input parameters

        Returns:
            Parsed input with intent and entities
        """
        logger.info("[OrchestratorAdapter] Parsing user input")

        user_message = params.get("user_message", "")
        message_lower = user_message.lower()

        # Simple intent detection
        intent = "unknown"
        entities = {}

        if any(kw in message_lower for kw in ["check inventory", "stock", "inventory"]):
            intent = "check_inventory"
        elif any(kw in message_lower for kw in ["yes", "approve", "ok", "proceed"]):
            intent = "approval"
            entities["decision"] = "approve"
        elif any(kw in message_lower for kw in ["no", "reject", "cancel"]):
            intent = "rejection"
            entities["decision"] = "reject"
        elif any(kw in message_lower for kw in ["help", "?"]):
            intent = "help"
        elif any(kw in message_lower for kw in ["quit", "exit", "bye"]):
            intent = "exit"

        return {
            "intent": intent,
            "entities": entities,
            "original_message": user_message,
            "confidence": 0.9 if intent != "unknown" else 0.3
        }

    def _coordinate_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a multi-agent workflow.

        Args:
            params: Input parameters

        Returns:
            Coordination results
        """
        logger.info("[OrchestratorAdapter] Coordinating workflow")

        workflow_type = params.get("workflow_type", "po_creation")
        initial_state = params.get("initial_state", {})

        if self.workflow is None:
            logger.warning("No workflow configured")
            return {
                "success": False,
                "error": "No workflow configured"
            }

        try:
            # Run the main orchestrator workflow
            result = self.workflow.invoke(initial_state)

            return {
                "success": True,
                "workflow_type": workflow_type,
                "result": result
            }

        except Exception as e:
            logger.error(f"Workflow coordination error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_response(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response to the user.

        Args:
            params: Input parameters

        Returns:
            Generated response
        """
        logger.info("[OrchestratorAdapter] Generating response")

        context = params.get("context", {})
        workflow_results = params.get("workflow_results", {})

        # Get response from workflow results if available
        response = workflow_results.get("agent_response", "")

        if not response:
            # Generate default response based on context
            stage = context.get("workflow_stage", "initial")

            if stage == "complete":
                response = "The operation has been completed successfully."
            elif stage == "error":
                response = "An error occurred during processing."
            else:
                response = "How can I help you today?"

        return {
            "response": response,
            "workflow_stage": context.get("workflow_stage", "initial")
        }

    def _process_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete user message.

        This is the main entry point for processing user messages,
        combining parsing, workflow coordination, and response generation.

        Args:
            params: Input parameters

        Returns:
            Complete processing result
        """
        logger.info("[OrchestratorAdapter] Processing message")

        user_message = params.get("user_message", "")
        conversation_history = params.get("conversation_history", [])
        workflow_state = params.get("workflow_state", {})

        if self.workflow is None:
            return {
                "success": False,
                "agent_response": "Orchestrator workflow not configured",
                "error": "No workflow"
            }

        # Prepare state
        state = {
            "user_message": user_message,
            "conversation_history": conversation_history,
            "workflow_stage": workflow_state.get("workflow_stage", "initial"),
            "pending_action": workflow_state.get("pending_action", "none"),
            "reorder_recommendations": workflow_state.get("reorder_recommendations", []),
            "supplier_recommendations": workflow_state.get("supplier_recommendations", []),
            "purchase_orders": workflow_state.get("purchase_orders", []),
            "inventory_summary": "",
            "supplier_summary": "",
            "po_summary": "",
            "agent_response": ""
        }

        try:
            # Run workflow
            result = self.workflow.invoke(state)

            return {
                "success": True,
                "agent_response": result.get("agent_response", ""),
                "workflow_stage": result.get("workflow_stage", "initial"),
                "pending_action": result.get("pending_action", "none"),
                "reorder_recommendations": result.get("reorder_recommendations", []),
                "supplier_recommendations": result.get("supplier_recommendations", []),
                "purchase_orders": result.get("purchase_orders", [])
            }

        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return {
                "success": False,
                "agent_response": f"An error occurred: {str(e)}",
                "error": str(e)
            }

    def get_agent_card(self) -> AgentCard:
        """Get the orchestrator agent card.

        Returns:
            Pre-defined orchestrator agent card
        """
        return ORCHESTRATOR_CARD
