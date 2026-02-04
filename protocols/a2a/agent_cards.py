"""Agent Cards - Agent capability definitions for A2A protocol.

This module provides utilities for loading, creating, and managing
agent cards which define agent capabilities for discovery.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentCapability(BaseModel):
    """Definition of a single agent capability.

    Attributes:
        name: Capability identifier (used in A2A method calls)
        description: Human-readable description
        input_schema: JSON Schema for capability inputs
        output_schema: JSON Schema for capability outputs
    """
    name: str = Field(..., description="Capability name")
    description: str = Field(default="", description="Capability description")
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """Agent card defining agent identity and capabilities.

    Agent cards are used for agent discovery in the A2A protocol.
    They describe what an agent can do and how to interact with it.

    Attributes:
        agent_id: Unique agent identifier
        name: Human-readable agent name
        description: Agent description
        version: Agent version string
        capabilities: List of capability names
        capability_details: Detailed capability definitions
        input_schema: Default input schema
        output_schema: Default output schema
        metadata: Additional metadata
    """
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Agent description")
    version: str = Field(default="1.0.0", description="Version string")
    capabilities: List[str] = Field(default_factory=list)
    capability_details: Dict[str, AgentCapability] = Field(default_factory=dict)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class AgentCardRegistry:
    """Registry for managing agent cards.

    Provides loading, caching, and lookup functionality for agent cards.

    Attributes:
        cards_dir: Directory containing agent card JSON files
        cards: Dictionary of agent_id -> AgentCard
    """
    cards_dir: Path
    cards: Dict[str, AgentCard] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize and load cards."""
        self.cards_dir = Path(self.cards_dir)
        self.load_all_cards()

    def load_all_cards(self) -> None:
        """Load all agent cards from the cards directory."""
        if not self.cards_dir.exists():
            logger.warning(f"Agent cards directory not found: {self.cards_dir}")
            return

        for card_file in self.cards_dir.glob("*.json"):
            try:
                card = self.load_card_from_file(card_file)
                if card:
                    self.cards[card.agent_id] = card
                    logger.info(f"Loaded agent card: {card.agent_id}")
            except Exception as e:
                logger.error(f"Failed to load agent card {card_file}: {e}")

        logger.info(f"Loaded {len(self.cards)} agent cards")

    def load_card_from_file(self, file_path: Path) -> Optional[AgentCard]:
        """Load an agent card from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            AgentCard or None if loading fails
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            return AgentCard(**data)
        except Exception as e:
            logger.error(f"Error loading card from {file_path}: {e}")
            return None

    def get_card(self, agent_id: str) -> Optional[AgentCard]:
        """Get an agent card by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentCard or None if not found
        """
        return self.cards.get(agent_id)

    def find_by_capability(self, capability: str) -> List[AgentCard]:
        """Find agents that support a capability.

        Args:
            capability: Capability name to search for

        Returns:
            List of agents supporting the capability
        """
        return [
            card for card in self.cards.values()
            if capability in card.capabilities
        ]

    def list_all_capabilities(self) -> Dict[str, List[str]]:
        """List all capabilities and the agents that provide them.

        Returns:
            Dictionary of capability -> list of agent_ids
        """
        capabilities: Dict[str, List[str]] = {}

        for agent_id, card in self.cards.items():
            for cap in card.capabilities:
                if cap not in capabilities:
                    capabilities[cap] = []
                capabilities[cap].append(agent_id)

        return capabilities

    def add_card(self, card: AgentCard) -> None:
        """Add or update an agent card.

        Args:
            card: AgentCard to add
        """
        self.cards[card.agent_id] = card
        logger.info(f"Added agent card: {card.agent_id}")

    def remove_card(self, agent_id: str) -> bool:
        """Remove an agent card.

        Args:
            agent_id: Agent identifier

        Returns:
            True if removed, False if not found
        """
        if agent_id in self.cards:
            del self.cards[agent_id]
            logger.info(f"Removed agent card: {agent_id}")
            return True
        return False

    def save_card(self, agent_id: str) -> bool:
        """Save an agent card to file.

        Args:
            agent_id: Agent identifier

        Returns:
            True if saved, False if not found
        """
        card = self.cards.get(agent_id)
        if not card:
            return False

        file_path = self.cards_dir / f"{agent_id}_card.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(card.model_dump(), f, indent=2)
            logger.info(f"Saved agent card to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving card: {e}")
            return False


def create_agent_card(
    agent_id: str,
    name: str,
    capabilities: List[str],
    description: str = "",
    version: str = "1.0.0",
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None
) -> AgentCard:
    """Create a new agent card.

    Args:
        agent_id: Unique agent identifier
        name: Human-readable name
        capabilities: List of capability names
        description: Agent description
        version: Version string
        input_schema: Default input schema
        output_schema: Default output schema

    Returns:
        New AgentCard instance
    """
    return AgentCard(
        agent_id=agent_id,
        name=name,
        description=description,
        version=version,
        capabilities=capabilities,
        input_schema=input_schema or {},
        output_schema=output_schema or {}
    )


def get_default_registry() -> AgentCardRegistry:
    """Get the default agent card registry.

    Returns:
        AgentCardRegistry loaded from config/agent_cards
    """
    cards_dir = Path(__file__).parent.parent.parent / "config" / "agent_cards"
    return AgentCardRegistry(cards_dir)


# Pre-defined agent cards for the PO Assistant system
INVENTORY_MONITOR_CARD = create_agent_card(
    agent_id="inventory_monitor",
    name="Inventory Monitor Agent",
    description="Monitors inventory levels and identifies items needing reorder",
    capabilities=["check_inventory", "calculate_reorder_quantities", "get_low_stock_items"],
    input_schema={
        "type": "object",
        "properties": {
            "check_all": {"type": "boolean", "description": "Check all items"},
            "product_ids": {"type": "array", "items": {"type": "string"}}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "low_stock_items": {"type": "array"},
            "reorder_recommendations": {"type": "array"}
        }
    }
)

SUPPLIER_SELECTOR_CARD = create_agent_card(
    agent_id="supplier_selector",
    name="Supplier Selector Agent",
    description="Queries suppliers and recommends best options based on price and availability",
    capabilities=["query_suppliers", "compare_suppliers", "get_supplier_quote"],
    input_schema={
        "type": "object",
        "properties": {
            "items_to_order": {"type": "array"},
            "supplier_ids": {"type": "array", "items": {"type": "string"}}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "supplier_recommendations": {"type": "array"},
            "quotes": {"type": "array"}
        }
    }
)

PURCHASE_ORDER_CARD = create_agent_card(
    agent_id="purchase_order",
    name="Purchase Order Agent",
    description="Creates and saves purchase order documents",
    capabilities=["create_po", "validate_po", "save_po"],
    input_schema={
        "type": "object",
        "properties": {
            "supplier_recommendations": {"type": "array"},
            "reorder_recommendations": {"type": "array"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "purchase_orders": {"type": "array"},
            "validation_results": {"type": "array"}
        }
    }
)

ORCHESTRATOR_CARD = create_agent_card(
    agent_id="orchestrator",
    name="Orchestrator Agent",
    description="Coordinates workflow and handles user interaction",
    capabilities=["parse_user_input", "coordinate_workflow", "generate_response"],
    input_schema={
        "type": "object",
        "properties": {
            "user_message": {"type": "string"},
            "conversation_history": {"type": "array"}
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "agent_response": {"type": "string"},
            "workflow_stage": {"type": "string"}
        }
    }
)
