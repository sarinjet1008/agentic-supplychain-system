"""Supplier Adapter - A2A adapter for Supplier Selector Agent.

This module provides an A2A adapter for the Supplier Selector Agent,
exposing supplier querying and comparison capabilities.
"""

import logging
from typing import Dict, Any, Optional, List

from protocols.a2a.adapters.base_adapter import BaseAgentAdapter, AdapterConfig
from protocols.a2a.agent_cards import AgentCard, SUPPLIER_SELECTOR_CARD

logger = logging.getLogger(__name__)


class SupplierAdapter(BaseAgentAdapter):
    """A2A adapter for the Supplier Selector Agent.

    Exposes the following capabilities:
    - query_suppliers: Query all suppliers for quotes
    - compare_suppliers: Compare supplier offers
    - get_supplier_quote: Get quote from a specific supplier
    """

    def __init__(
        self,
        workflow: Optional[Any] = None,
        router: Optional[Any] = None
    ):
        """Initialize the supplier adapter.

        Args:
            workflow: Compiled supplier workflow
            router: Optional A2A router
        """
        config = AdapterConfig(
            agent_id="supplier_selector",
            agent_name="Supplier Selector Agent",
            version="1.0.0"
        )
        super().__init__(config, workflow, router)

    def _register_handlers(self) -> None:
        """Register supplier-specific handlers."""

        self.server.register_handler(
            method="query_suppliers",
            handler=self._query_suppliers,
            description="Query all suppliers for quotes on specified items",
            input_schema={
                "type": "object",
                "properties": {
                    "items_to_order": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "integer"}
                            }
                        },
                        "description": "Items to get quotes for"
                    },
                    "supplier_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional specific suppliers to query"
                    }
                },
                "required": ["items_to_order"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "quotes": {"type": "array"},
                    "best_options": {"type": "array"}
                }
            }
        )

        self.server.register_handler(
            method="compare_suppliers",
            handler=self._compare_suppliers,
            description="Compare quotes from multiple suppliers",
            input_schema={
                "type": "object",
                "properties": {
                    "quotes": {
                        "type": "array",
                        "description": "Quotes to compare"
                    },
                    "criteria": {
                        "type": "string",
                        "enum": ["price", "lead_time", "rating"],
                        "description": "Primary comparison criteria"
                    }
                }
            }
        )

        self.server.register_handler(
            method="get_supplier_quote",
            handler=self._get_supplier_quote,
            description="Get a quote from a specific supplier",
            input_schema={
                "type": "object",
                "properties": {
                    "supplier_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"}
                },
                "required": ["supplier_id", "product_id", "quantity"]
            }
        )

    def _query_suppliers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query suppliers for quotes.

        Args:
            params: Input parameters with items_to_order

        Returns:
            Quotes and recommendations
        """
        logger.info("[SupplierAdapter] Querying suppliers")

        items_to_order = params.get("items_to_order", [])

        if self.workflow is None:
            logger.warning("No workflow configured")
            return {
                "quotes": [],
                "best_options": [],
                "summary": "No workflow configured"
            }

        # Prepare workflow state
        state = {
            "reorder_recommendations": items_to_order,
            "supplier_recommendations": [],
            "supplier_summary": ""
        }

        # Run workflow
        result = self.workflow.invoke(state)

        return {
            "quotes": result.get("supplier_recommendations", []),
            "best_options": self._extract_best_options(
                result.get("supplier_recommendations", [])
            ),
            "summary": result.get("supplier_summary", "")
        }

    def _compare_suppliers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare supplier quotes.

        Args:
            params: Input parameters with quotes

        Returns:
            Comparison results
        """
        logger.info("[SupplierAdapter] Comparing suppliers")

        quotes = params.get("quotes", [])
        criteria = params.get("criteria", "price")

        if not quotes:
            return {
                "comparison": [],
                "winner": None,
                "reason": "No quotes to compare"
            }

        # Sort by criteria
        if criteria == "price":
            sorted_quotes = sorted(quotes, key=lambda q: q.get("total_cost", float('inf')))
        elif criteria == "lead_time":
            sorted_quotes = sorted(quotes, key=lambda q: q.get("lead_time_days", float('inf')))
        elif criteria == "rating":
            sorted_quotes = sorted(quotes, key=lambda q: q.get("rating", 0), reverse=True)
        else:
            sorted_quotes = quotes

        winner = sorted_quotes[0] if sorted_quotes else None

        return {
            "comparison": sorted_quotes,
            "winner": winner,
            "criteria": criteria,
            "reason": f"Best {criteria} among {len(quotes)} options"
        }

    def _get_supplier_quote(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get quote from a specific supplier.

        Args:
            params: Input parameters

        Returns:
            Quote from supplier
        """
        logger.info("[SupplierAdapter] Getting supplier quote")

        supplier_id = params.get("supplier_id")
        product_id = params.get("product_id")
        quantity = params.get("quantity", 1)

        # Try to use API MCP server if available
        try:
            from protocols.mcp.api_server import get_supplier_quote
            quote = get_supplier_quote(supplier_id, product_id, quantity)
            return {
                "supplier_id": supplier_id,
                "product_id": product_id,
                "quantity": quantity,
                "quote": quote
            }
        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return {
                "supplier_id": supplier_id,
                "product_id": product_id,
                "quantity": quantity,
                "error": str(e)
            }

    def _extract_best_options(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract best option for each product.

        Args:
            recommendations: All supplier recommendations

        Returns:
            Best option per product
        """
        best_by_product: Dict[str, Dict[str, Any]] = {}

        for rec in recommendations:
            product_id = rec.get("product_id")
            if not product_id:
                continue

            current_best = best_by_product.get(product_id)
            if not current_best:
                best_by_product[product_id] = rec
            elif rec.get("total_cost", float('inf')) < current_best.get("total_cost", float('inf')):
                best_by_product[product_id] = rec

        return list(best_by_product.values())

    def get_agent_card(self) -> AgentCard:
        """Get the supplier agent card.

        Returns:
            Pre-defined supplier agent card
        """
        return SUPPLIER_SELECTOR_CARD
