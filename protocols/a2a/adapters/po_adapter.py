"""PO Adapter - A2A adapter for Purchase Order Agent.

This module provides an A2A adapter for the Purchase Order Agent,
exposing PO creation, validation, and saving capabilities.
"""

import logging
from typing import Dict, Any, Optional, List

from protocols.a2a.adapters.base_adapter import BaseAgentAdapter, AdapterConfig
from protocols.a2a.agent_cards import AgentCard, PURCHASE_ORDER_CARD

logger = logging.getLogger(__name__)


class POAdapter(BaseAgentAdapter):
    """A2A adapter for the Purchase Order Agent.

    Exposes the following capabilities:
    - create_po: Create purchase order documents
    - validate_po: Validate a purchase order
    - save_po: Save PO to filesystem
    """

    def __init__(
        self,
        workflow: Optional[Any] = None,
        router: Optional[Any] = None
    ):
        """Initialize the PO adapter.

        Args:
            workflow: Compiled PO workflow
            router: Optional A2A router
        """
        config = AdapterConfig(
            agent_id="purchase_order",
            agent_name="Purchase Order Agent",
            version="1.0.0"
        )
        super().__init__(config, workflow, router)

    def _register_handlers(self) -> None:
        """Register PO-specific handlers."""

        self.server.register_handler(
            method="create_po",
            handler=self._create_po,
            description="Create purchase order documents from recommendations",
            input_schema={
                "type": "object",
                "properties": {
                    "supplier_recommendations": {
                        "type": "array",
                        "description": "Supplier recommendations with items"
                    },
                    "reorder_recommendations": {
                        "type": "array",
                        "description": "Items to order"
                    }
                },
                "required": ["supplier_recommendations"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "purchase_orders": {"type": "array"},
                    "validation_results": {"type": "array"}
                }
            }
        )

        self.server.register_handler(
            method="validate_po",
            handler=self._validate_po,
            description="Validate a purchase order",
            input_schema={
                "type": "object",
                "properties": {
                    "purchase_order": {
                        "type": "object",
                        "description": "PO to validate"
                    }
                },
                "required": ["purchase_order"]
            }
        )

        self.server.register_handler(
            method="save_po",
            handler=self._save_po,
            description="Save a purchase order to the filesystem",
            input_schema={
                "type": "object",
                "properties": {
                    "purchase_order": {
                        "type": "object",
                        "description": "PO to save"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "pdf"],
                        "description": "Output format"
                    }
                },
                "required": ["purchase_order"]
            }
        )

    def _create_po(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create purchase orders.

        Args:
            params: Input parameters

        Returns:
            Created POs and validation results
        """
        logger.info("[POAdapter] Creating purchase orders")

        supplier_recommendations = params.get("supplier_recommendations", [])
        reorder_recommendations = params.get("reorder_recommendations", [])

        if self.workflow is None:
            logger.warning("No workflow configured")
            return {
                "purchase_orders": [],
                "validation_results": [],
                "summary": "No workflow configured"
            }

        # Prepare workflow state
        state = {
            "supplier_recommendations": supplier_recommendations,
            "reorder_recommendations": reorder_recommendations,
            "purchase_orders": [],
            "validation_results": [],
            "po_summary": ""
        }

        # Run workflow
        result = self.workflow.invoke(state)

        return {
            "purchase_orders": result.get("purchase_orders", []),
            "validation_results": result.get("validation_results", []),
            "summary": result.get("po_summary", "")
        }

    def _validate_po(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a purchase order.

        Args:
            params: Input parameters with purchase_order

        Returns:
            Validation results
        """
        logger.info("[POAdapter] Validating purchase order")

        po_data = params.get("purchase_order", {})

        try:
            from agent.purchase_order.models import PurchaseOrder
            from agent.purchase_order.validator import validate_purchase_order

            # Create PO object if needed
            if isinstance(po_data, dict):
                po = PurchaseOrder(**po_data)
            else:
                po = po_data

            # Run validation
            result = validate_purchase_order(po)

            return {
                "is_valid": result.is_valid,
                "issues": [
                    {
                        "code": issue.code,
                        "message": issue.message,
                        "severity": issue.severity.value
                    }
                    for issue in result.issues
                ],
                "po_number": po.po_number
            }

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "is_valid": False,
                "issues": [{"code": "ERROR", "message": str(e), "severity": "error"}],
                "error": str(e)
            }

    def _save_po(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save a purchase order.

        Args:
            params: Input parameters

        Returns:
            Save result
        """
        logger.info("[POAdapter] Saving purchase order")

        po_data = params.get("purchase_order", {})
        output_format = params.get("format", "json")

        try:
            from protocols.mcp.filesystem_server import FilesystemMCPServer

            fs_server = FilesystemMCPServer()

            if output_format == "json":
                # Save as JSON
                po_number = po_data.get("po_number", "unknown")
                result = fs_server.execute_tool(
                    "write_json",
                    filename=f"{po_number}.json",
                    data=po_data
                )

                return {
                    "success": result.success,
                    "file_path": result.data.get("file_path") if result.success else None,
                    "format": output_format
                }
            else:
                return {
                    "success": False,
                    "error": f"Format not supported: {output_format}"
                }

        except Exception as e:
            logger.error(f"Save error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_agent_card(self) -> AgentCard:
        """Get the PO agent card.

        Returns:
            Pre-defined PO agent card
        """
        return PURCHASE_ORDER_CARD
