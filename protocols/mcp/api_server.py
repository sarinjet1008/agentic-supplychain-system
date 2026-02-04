"""API MCP Server - Simulates external supplier API calls.

This MCP server simulates real-world API calls to supplier systems,
including realistic delays, price variations, and occasional errors.
This demonstrates how MCP can be used to integrate with external services.
"""

import logging
import random
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from protocols.mcp.base_server import (
    BaseMCPServer,
    MCPError,
    MCPErrorCode
)

logger = logging.getLogger(__name__)

# Backward compatibility alias
APIError = MCPError


class SupplierAPIConfig(BaseModel):
    """Configuration for a supplier API endpoint.

    Attributes:
        supplier_id: Unique supplier identifier
        api_url: Simulated API endpoint URL
        delay_min: Minimum response delay in seconds
        delay_max: Maximum response delay in seconds
        price_variation: Price variation percentage (e.g., 0.1 = ±10%)
        error_rate: Probability of API error (0.0 to 1.0)
    """
    supplier_id: str
    api_url: str
    delay_min: float = 0.5
    delay_max: float = 2.0
    price_variation: float = 0.10
    error_rate: float = 0.05


class QuoteRequest(BaseModel):
    """Request for a price quote from supplier.

    Attributes:
        product_id: Product identifier
        quantity: Quantity to order
        supplier_id: Target supplier
    """
    product_id: str
    quantity: int
    supplier_id: str


class QuoteResponse(BaseModel):
    """Response from supplier API with quote.

    Attributes:
        product_id: Product identifier
        quantity: Quoted quantity
        unit_price: Price per unit
        total_price: Total price (quantity * unit_price)
        lead_time_days: Estimated delivery time in days
        available_stock: Current stock available
        supplier_id: Responding supplier
    """
    product_id: str
    quantity: int
    unit_price: float
    total_price: float
    lead_time_days: int
    available_stock: int
    supplier_id: str


class SupplierAPIMCPServer(BaseMCPServer):
    """MCP Server for simulated supplier API integration.

    This server simulates external API calls to supplier systems, providing:
    - Realistic network delays (0.5-2.0 seconds)
    - Price variations (±10% from base price)
    - Occasional errors to test resilience
    - Stock availability checks

    Inherits from BaseMCPServer for tool registration, error handling,
    and health check capabilities.
    """

    def __init__(self, suppliers_file: Optional[str] = None):
        """Initialize the API MCP server.

        Args:
            suppliers_file: Path to suppliers.json file with base pricing
        """
        if suppliers_file is None:
            suppliers_file = Path(__file__).parent.parent.parent / "data" / "suppliers.json"
        else:
            suppliers_file = Path(suppliers_file)

        self.suppliers_file = suppliers_file
        self.suppliers_data = self._load_suppliers()

        # Configure API endpoints for each supplier
        self.api_configs = {
            "SUP001": SupplierAPIConfig(
                supplier_id="SUP001",
                api_url="https://api.techworld.com/quotes",
                delay_min=0.5,
                delay_max=1.5,
                price_variation=0.08,
                error_rate=0.02
            ),
            "SUP002": SupplierAPIConfig(
                supplier_id="SUP002",
                api_url="https://api.globalelectronics.com/pricing",
                delay_min=0.7,
                delay_max=2.0,
                price_variation=0.12,
                error_rate=0.05
            ),
            "SUP003": SupplierAPIConfig(
                supplier_id="SUP003",
                api_url="https://api.officeplus.com/quote",
                delay_min=0.3,
                delay_max=1.0,
                price_variation=0.10,
                error_rate=0.01
            )
        }

        # Initialize base server
        super().__init__(
            server_id="supplier_api_mcp",
            name="Supplier API MCP Server",
            version="1.1.0"
        )

    def _register_tools(self) -> None:
        """Register API tools."""
        self.register_tool(
            name="get_supplier_quote",
            handler=self._get_supplier_quote,
            description="Get a price quote from a supplier API",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product identifier"},
                    "quantity": {"type": "integer", "description": "Quantity to order"},
                    "supplier_id": {"type": "string", "description": "Supplier identifier"}
                },
                "required": ["product_id", "quantity", "supplier_id"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "unit_price": {"type": "number"},
                    "total_price": {"type": "number"},
                    "lead_time_days": {"type": "integer"},
                    "available_stock": {"type": "integer"},
                    "supplier_id": {"type": "string"}
                }
            }
        )

        self.register_tool(
            name="get_quotes_batch",
            handler=self._get_quotes_batch,
            description="Get quotes from multiple suppliers for a product",
            input_schema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product identifier"},
                    "quantity": {"type": "integer", "description": "Quantity to order"},
                    "supplier_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of supplier IDs (optional, defaults to all)"
                    }
                },
                "required": ["product_id", "quantity"]
            },
            output_schema={
                "type": "object",
                "additionalProperties": {"type": "object"}
            }
        )

        self.register_tool(
            name="check_supplier_availability",
            handler=self._check_supplier_availability,
            description="Check if a supplier API is available (health check)",
            input_schema={
                "type": "object",
                "properties": {
                    "supplier_id": {"type": "string", "description": "Supplier identifier"}
                },
                "required": ["supplier_id"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "supplier_id": {"type": "string"},
                    "available": {"type": "boolean"},
                    "api_url": {"type": "string"},
                    "response_time_ms": {"type": "integer"}
                }
            }
        )

        self.register_tool(
            name="list_suppliers",
            handler=self._list_suppliers,
            description="List all available suppliers and their API configurations",
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "supplier_id": {"type": "string"},
                        "api_url": {"type": "string"},
                        "error_rate": {"type": "number"}
                    }
                }
            }
        )

    def _get_description(self) -> str:
        """Get server description."""
        return "Simulates external supplier API calls with realistic delays and price variations"

    def _load_suppliers(self) -> Dict[str, Any]:
        """Load supplier data from JSON file.

        Handles the suppliers.json format which has:
        - Root object with "suppliers" key
        - Supplier uses "id" not "supplier_id"
        - Catalog is a dict keyed by product_id
        """
        try:
            with open(self.suppliers_file, 'r') as f:
                data = json.load(f)

            # Handle root object with "suppliers" key
            if isinstance(data, dict) and "suppliers" in data:
                suppliers_list = data["suppliers"]
            elif isinstance(data, list):
                suppliers_list = data
            else:
                logger.error("Invalid suppliers.json format")
                return {}

            # Convert to dict keyed by supplier_id, normalizing the format
            result = {}
            for supplier in suppliers_list:
                # Use "id" or "supplier_id" depending on what's available
                supplier_id = supplier.get("supplier_id") or supplier.get("id")
                if not supplier_id:
                    continue

                # Normalize catalog format: convert dict to list if needed
                raw_catalog = supplier.get("catalog", {})
                if isinstance(raw_catalog, dict):
                    # Convert {product_id: {details}} to [{product_id, details}]
                    catalog_list = []
                    for prod_id, prod_data in raw_catalog.items():
                        item = {"product_id": prod_id, **prod_data}
                        catalog_list.append(item)
                    supplier["catalog"] = catalog_list

                # Store with supplier_id as key
                supplier["supplier_id"] = supplier_id
                result[supplier_id] = supplier

            logger.info(f"Loaded {len(result)} suppliers from {self.suppliers_file}")
            return result

        except Exception as e:
            logger.error(f"Failed to load suppliers: {e}")
            return {}

    def _get_supplier_quote(
        self,
        product_id: str,
        quantity: int,
        supplier_id: str
    ) -> Dict[str, Any]:
        """Get a price quote from a supplier API.

        This simulates an API call with realistic delays and price variations.

        Args:
            product_id: Product to quote
            quantity: Quantity needed
            supplier_id: Supplier to query

        Returns:
            QuoteResponse as dictionary

        Raises:
            MCPError: If API call fails (simulated errors)
        """
        logger.info(f"[API MCP] Requesting quote from {supplier_id} for {product_id} (qty: {quantity})")

        # Get API configuration
        api_config = self.api_configs.get(supplier_id)
        if not api_config:
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"Unknown supplier: {supplier_id}",
                {"supplier_id": supplier_id, "available": list(self.api_configs.keys())}
            )

        # Simulate network delay
        delay = random.uniform(api_config.delay_min, api_config.delay_max)
        logger.debug(f"[API MCP] Simulating API delay: {delay:.2f}s")
        time.sleep(delay)

        # Simulate occasional API errors
        if random.random() < api_config.error_rate:
            error_messages = [
                "Connection timeout",
                "Service temporarily unavailable",
                "Rate limit exceeded",
                "Invalid API key"
            ]
            error_msg = random.choice(error_messages)
            logger.warning(f"[API MCP] Simulated API error: {error_msg}")
            raise MCPError(
                MCPErrorCode.CONNECTION_ERROR,
                f"API call failed: {error_msg}",
                {"supplier_id": supplier_id, "simulated": True}
            )

        # Get base supplier data
        supplier = self.suppliers_data.get(supplier_id)
        if not supplier:
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"Supplier data not found: {supplier_id}",
                {"supplier_id": supplier_id}
            )

        # Find product in catalog
        product = None
        for item in supplier.get("catalog", []):
            if item["product_id"] == product_id:
                product = item
                break

        if not product:
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"Product {product_id} not available from {supplier_id}",
                {"product_id": product_id, "supplier_id": supplier_id}
            )

        # Apply price variation (simulating market fluctuations)
        base_price = product["unit_price"]
        variation = random.uniform(-api_config.price_variation, api_config.price_variation)
        current_price = base_price * (1 + variation)
        current_price = round(current_price, 2)

        # Simulate stock availability (random between 50-500)
        available_stock = random.randint(50, 500)

        # Calculate total
        total_price = round(current_price * quantity, 2)

        # Create response
        quote = QuoteResponse(
            product_id=product_id,
            quantity=quantity,
            unit_price=current_price,
            total_price=total_price,
            lead_time_days=product.get("lead_time_days", 7),
            available_stock=available_stock,
            supplier_id=supplier_id
        )

        logger.info(
            f"[API MCP] Quote received: {supplier_id} - {product_id} "
            f"@ ${current_price:.2f}/unit (total: ${total_price:.2f})"
        )

        return quote.model_dump()

    def _get_quotes_batch(
        self,
        product_id: str,
        quantity: int,
        supplier_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get quotes from multiple suppliers (simulated parallel).

        Args:
            product_id: Product to quote
            quantity: Quantity needed
            supplier_ids: List of supplier IDs (defaults to all)

        Returns:
            Dictionary with quotes and errors
        """
        if supplier_ids is None:
            supplier_ids = list(self.api_configs.keys())

        logger.info(f"[API MCP] Requesting batch quotes for {product_id} from {len(supplier_ids)} suppliers")

        quotes = {}
        errors = {}

        for supplier_id in supplier_ids:
            try:
                quote = self._get_supplier_quote(product_id, quantity, supplier_id)
                quotes[supplier_id] = quote
            except MCPError as e:
                logger.warning(f"[API MCP] Failed to get quote from {supplier_id}: {e.message}")
                errors[supplier_id] = {"error": e.message, "code": e.code.value}

        logger.info(f"[API MCP] Batch complete: {len(quotes)} quotes, {len(errors)} errors")

        return {"quotes": quotes, "errors": errors}

    def _check_supplier_availability(self, supplier_id: str) -> Dict[str, Any]:
        """Check if a supplier API is available (health check).

        Args:
            supplier_id: Supplier to check

        Returns:
            Dictionary with availability status
        """
        api_config = self.api_configs.get(supplier_id)
        if not api_config:
            return {"supplier_id": supplier_id, "available": False, "error": "Unknown supplier"}

        # Simulate health check delay
        time.sleep(0.1)

        # 95% uptime simulation
        is_available = random.random() > 0.05

        return {
            "supplier_id": supplier_id,
            "available": is_available,
            "api_url": api_config.api_url,
            "response_time_ms": random.randint(50, 300)
        }

    def _list_suppliers(self) -> List[Dict[str, Any]]:
        """List all available suppliers and their API configurations.

        Returns:
            List of supplier API configurations
        """
        return [
            {
                "supplier_id": config.supplier_id,
                "api_url": config.api_url,
                "delay_range": f"{config.delay_min}-{config.delay_max}s",
                "price_variation": f"±{config.price_variation * 100:.0f}%",
                "error_rate": f"{config.error_rate * 100:.1f}%"
            }
            for config in self.api_configs.values()
        ]

    # Backward-compatible convenience methods
    def get_supplier_quote(
        self,
        product_id: str,
        quantity: int,
        supplier_id: str
    ) -> QuoteResponse:
        """Get a supplier quote (backward-compatible method)."""
        result = self.execute_tool(
            "get_supplier_quote",
            product_id=product_id,
            quantity=quantity,
            supplier_id=supplier_id
        )
        if result.success:
            return QuoteResponse(**result.data)
        raise MCPError(
            MCPErrorCode(result.error["code"]),
            result.error["message"]
        )

    def get_quotes_batch(
        self,
        product_id: str,
        quantity: int,
        supplier_ids: Optional[List[str]] = None
    ) -> Dict[str, QuoteResponse]:
        """Get quotes from multiple suppliers (backward-compatible method)."""
        result = self.execute_tool(
            "get_quotes_batch",
            product_id=product_id,
            quantity=quantity,
            supplier_ids=supplier_ids
        )
        if result.success:
            return {
                sid: QuoteResponse(**quote)
                for sid, quote in result.data.get("quotes", {}).items()
            }
        raise MCPError(
            MCPErrorCode(result.error["code"]),
            result.error["message"]
        )

    def check_supplier_availability(self, supplier_id: str) -> Dict[str, Any]:
        """Check supplier availability (backward-compatible method)."""
        result = self.execute_tool("check_supplier_availability", supplier_id=supplier_id)
        if result.success:
            return result.data
        raise MCPError(
            MCPErrorCode(result.error["code"]),
            result.error["message"]
        )


# Convenience functions for agents to use

_api_server: Optional[SupplierAPIMCPServer] = None


def get_api_server() -> SupplierAPIMCPServer:
    """Get or create the global API MCP server instance."""
    global _api_server
    if _api_server is None:
        _api_server = SupplierAPIMCPServer()
    return _api_server


def get_supplier_quote(product_id: str, quantity: int, supplier_id: str) -> Dict[str, Any]:
    """Get a supplier quote (convenience function).

    Args:
        product_id: Product identifier
        quantity: Quantity needed
        supplier_id: Supplier to query

    Returns:
        Quote as dictionary
    """
    server = get_api_server()
    try:
        quote = server.get_supplier_quote(product_id, quantity, supplier_id)
        return quote.model_dump()
    except MCPError as e:
        logger.error(f"API call failed: {e}")
        return {"error": str(e), "supplier_id": supplier_id}
