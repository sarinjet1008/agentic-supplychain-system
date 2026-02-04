"""Inventory Adapter - A2A adapter for Inventory Monitor Agent.

This module provides an A2A adapter for the Inventory Monitor Agent,
exposing inventory checking and reorder calculation capabilities.
"""

import logging
from typing import Dict, Any, Optional

from protocols.a2a.adapters.base_adapter import BaseAgentAdapter, AdapterConfig
from protocols.a2a.agent_cards import AgentCard, INVENTORY_MONITOR_CARD

logger = logging.getLogger(__name__)


class InventoryAdapter(BaseAgentAdapter):
    """A2A adapter for the Inventory Monitor Agent.

    Exposes the following capabilities:
    - check_inventory: Check inventory levels
    - calculate_reorder_quantities: Calculate reorder recommendations
    - get_low_stock_items: Get items below reorder point
    """

    def __init__(
        self,
        workflow: Optional[Any] = None,
        router: Optional[Any] = None
    ):
        """Initialize the inventory adapter.

        Args:
            workflow: Compiled inventory workflow
            router: Optional A2A router
        """
        config = AdapterConfig(
            agent_id="inventory_monitor",
            agent_name="Inventory Monitor Agent",
            version="1.0.0"
        )
        super().__init__(config, workflow, router)

    def _register_handlers(self) -> None:
        """Register inventory-specific handlers."""

        self.server.register_handler(
            method="check_inventory",
            handler=self._check_inventory,
            description="Check inventory levels and identify low stock items",
            input_schema={
                "type": "object",
                "properties": {
                    "check_all": {
                        "type": "boolean",
                        "description": "Check all items (default: true)"
                    },
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific product IDs to check"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "low_stock_items": {"type": "array"},
                    "reorder_recommendations": {"type": "array"},
                    "summary": {"type": "string"}
                }
            }
        )

        self.server.register_handler(
            method="calculate_reorder_quantities",
            handler=self._calculate_reorder_quantities,
            description="Calculate recommended reorder quantities",
            input_schema={
                "type": "object",
                "properties": {
                    "low_stock_items": {
                        "type": "array",
                        "description": "Items to calculate reorders for"
                    }
                }
            }
        )

        self.server.register_handler(
            method="get_low_stock_items",
            handler=self._get_low_stock_items,
            description="Get all items currently below reorder point",
            input_schema={"type": "object", "properties": {}}
        )

    def _check_inventory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check inventory levels.

        Args:
            params: Input parameters

        Returns:
            Inventory check results
        """
        logger.info("[InventoryAdapter] Checking inventory")

        if self.workflow is None:
            logger.warning("No workflow configured, returning empty results")
            return {
                "low_stock_items": [],
                "reorder_recommendations": [],
                "summary": "No workflow configured"
            }

        # Prepare workflow state
        state = {
            "user_message": "check inventory",
            "workflow_stage": "initial",
            "pending_action": "none",
            "reorder_recommendations": [],
            "inventory_summary": "",
            "agent_response": ""
        }

        # Run workflow
        result = self.workflow.invoke(state)

        return {
            "low_stock_items": [
                rec.model_dump() if hasattr(rec, 'model_dump') else rec
                for rec in result.get("reorder_recommendations", [])
            ],
            "reorder_recommendations": result.get("reorder_recommendations", []),
            "summary": result.get("inventory_summary", "")
        }

    def _calculate_reorder_quantities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate reorder quantities.

        Args:
            params: Input parameters with low_stock_items

        Returns:
            Reorder calculations
        """
        logger.info("[InventoryAdapter] Calculating reorder quantities")

        low_stock_items = params.get("low_stock_items", [])

        # Simple calculation - in production this would be more sophisticated
        recommendations = []
        for item in low_stock_items:
            reorder_qty = item.get("reorder_quantity", 50)
            recommendations.append({
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "current_stock": item.get("current_stock", 0),
                "reorder_quantity": reorder_qty,
                "reason": "Below reorder point"
            })

        return {
            "recommendations": recommendations,
            "total_items": len(recommendations)
        }

    def _get_low_stock_items(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get items below reorder point.

        Args:
            params: Input parameters (unused)

        Returns:
            Low stock items
        """
        logger.info("[InventoryAdapter] Getting low stock items")

        # Use check_inventory and filter
        result = self._check_inventory({"check_all": True})

        return {
            "items": result.get("low_stock_items", []),
            "count": len(result.get("low_stock_items", []))
        }

    def get_agent_card(self) -> AgentCard:
        """Get the inventory agent card.

        Returns:
            Pre-defined inventory agent card
        """
        return INVENTORY_MONITOR_CARD
