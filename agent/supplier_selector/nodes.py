"""Node functions for Supplier Selector Agent."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List
from agent.supplier_selector.models import SupplierState, SupplierQuote, SupplierRecommendation
from protocols.mcp.api_server import get_api_server, APIError

logger = logging.getLogger(__name__)

# Configuration: Use API MCP server for real-time quotes (set USE_API_MCP=true in .env)
USE_API_MCP = os.getenv("USE_API_MCP", "false").lower() == "true"


def load_suppliers(state: SupplierState) -> Dict[str, Any]:
    """
    Load supplier data from JSON file.

    Args:
        state: Current workflow state

    Returns:
        Updated state with supplier data
    """
    logger.info("Loading supplier data...")

    try:
        supplier_file = Path("data/suppliers.json")
        with open(supplier_file, 'r') as f:
            supplier_data = json.load(f)

        logger.info(f"Loaded {len(supplier_data['suppliers'])} suppliers")

        return {"supplier_data": supplier_data}

    except Exception as e:
        logger.error(f"Error loading supplier data: {e}")
        return {
            "supplier_data": {"suppliers": []},
            "summary_message": f"❌ Error loading supplier data: {str(e)}"
        }


def collect_quotes(state: SupplierState) -> Dict[str, Any]:
    """
    Collect quotes from all suppliers for the requested items.

    Can use either:
    1. Static pricing from suppliers.json (default)
    2. API MCP Server for real-time quotes with price variations (if USE_API_MCP=true)

    Args:
        state: Current workflow state

    Returns:
        Updated state with all quotes
    """
    logger.info(f"Collecting quotes from suppliers (API MCP: {'enabled' if USE_API_MCP else 'disabled'})...")

    items_to_source = state["items_to_source"]
    supplier_data = state["supplier_data"]
    all_quotes: List[SupplierQuote] = []

    try:
        if USE_API_MCP:
            # Use API MCP Server for real-time quotes with realistic delays and price variations
            logger.info("[MCP API] Using API MCP Server for supplier quotes")
            api_server = get_api_server()

            for item in items_to_source:
                product_id = item["product_id"]
                quantity_needed = item["quantity_needed"]

                # Query each supplier via API MCP
                for supplier in supplier_data["suppliers"]:
                    supplier_id = supplier["id"]
                    supplier_name = supplier["name"]
                    catalog = supplier.get("catalog", {})

                    # Check if supplier has this product
                    if product_id in catalog:
                        product_info = catalog[product_id]

                        try:
                            # Get real-time quote via API MCP (with simulated delays and price variations)
                            api_quote = api_server.get_supplier_quote(
                                product_id=product_id,
                                quantity=quantity_needed,
                                supplier_id=supplier_id
                            )

                            quote = SupplierQuote(
                                supplier_id=supplier_id,
                                supplier_name=supplier_name,
                                product_id=product_id,
                                product_name=product_info["product_name"],
                                unit_price=api_quote.unit_price,  # Real-time price from API
                                lead_time_days=api_quote.lead_time_days,
                                min_order_quantity=product_info["min_order_quantity"],
                                quantity_needed=max(quantity_needed, product_info["min_order_quantity"]),
                                total_cost=api_quote.unit_price * max(quantity_needed, product_info["min_order_quantity"])
                            )

                            all_quotes.append(quote)
                            logger.debug(
                                f"[MCP API] Got quote from {supplier_name}: "
                                f"${api_quote.unit_price:.2f}/unit (±{api_server.api_configs[supplier_id].price_variation*100:.0f}% variation)"
                            )

                        except APIError as api_err:
                            logger.warning(f"[MCP API] Failed to get quote from {supplier_name}: {api_err}")
                            # Continue to next supplier

            logger.info(f"[MCP API] Collected {len(all_quotes)} quotes via API (some suppliers may have failed)")

        else:
            # Use static pricing from suppliers.json
            logger.info("Using static pricing from suppliers.json")

            for item in items_to_source:
                product_id = item["product_id"]
                quantity_needed = item["quantity_needed"]

                # Query each supplier
                for supplier in supplier_data["suppliers"]:
                    supplier_id = supplier["id"]
                    supplier_name = supplier["name"]
                    catalog = supplier.get("catalog", {})

                    # Check if supplier has this product
                    if product_id in catalog:
                        product_info = catalog[product_id]

                        quote = SupplierQuote(
                            supplier_id=supplier_id,
                            supplier_name=supplier_name,
                            product_id=product_id,
                            product_name=product_info["product_name"],
                            unit_price=product_info["unit_price"],
                            lead_time_days=product_info["lead_time_days"],
                            min_order_quantity=product_info["min_order_quantity"],
                            quantity_needed=max(quantity_needed, product_info["min_order_quantity"]),
                            total_cost=product_info["unit_price"] * max(quantity_needed, product_info["min_order_quantity"])
                        )

                        all_quotes.append(quote)

            logger.info(f"Collected {len(all_quotes)} quotes from suppliers")

        return {"all_quotes": all_quotes}

    except Exception as e:
        logger.error(f"Error collecting quotes: {e}")
        return {
            "all_quotes": [],
            "summary_message": f"❌ Error collecting quotes: {str(e)}"
        }


def analyze_and_recommend(state: SupplierState) -> Dict[str, Any]:
    """
    Analyze quotes and recommend best supplier for each item.

    Strategy:
    - Calculate total cost (including min order quantities)
    - Consider lead time as secondary factor
    - Prefer lower cost, then faster delivery

    Args:
        state: Current workflow state

    Returns:
        Updated state with recommendations
    """
    logger.info("Analyzing quotes and generating recommendations...")

    all_quotes = state["all_quotes"]
    recommendations: List[SupplierRecommendation] = []

    try:
        # Group quotes by product
        quotes_by_product: Dict[str, List[SupplierQuote]] = {}
        for quote in all_quotes:
            if quote.product_id not in quotes_by_product:
                quotes_by_product[quote.product_id] = []
            quotes_by_product[quote.product_id].append(quote)

        # Find best quote for each product
        for product_id, product_quotes in quotes_by_product.items():
            # Sort by total cost (primary) and lead time (secondary)
            sorted_quotes = sorted(
                product_quotes,
                key=lambda q: (q.total_cost, q.lead_time_days)
            )

            best_quote = sorted_quotes[0]

            # Determine reason for recommendation
            if len(sorted_quotes) == 1:
                reason = "Only supplier available"
            else:
                second_best = sorted_quotes[1]
                savings = second_best.total_cost - best_quote.total_cost
                if savings > 0:
                    reason = f"Lowest cost (saves ${savings:.2f})"
                elif best_quote.lead_time_days < second_best.lead_time_days:
                    days_faster = second_best.lead_time_days - best_quote.lead_time_days
                    reason = f"Fastest delivery ({days_faster} days faster)"
                else:
                    reason = "Best overall value"

            recommendation = SupplierRecommendation(
                product_id=best_quote.product_id,
                product_name=best_quote.product_name,
                quantity_needed=best_quote.quantity_needed,
                recommended_supplier_id=best_quote.supplier_id,
                recommended_supplier_name=best_quote.supplier_name,
                unit_price=best_quote.unit_price,
                total_cost=best_quote.total_cost,
                lead_time_days=best_quote.lead_time_days,
                reason=reason
            )

            recommendations.append(recommendation)

        # Generate summary message
        summary_parts = [f"📊 Supplier Analysis Complete - Found best prices for {len(recommendations)} item(s):\n"]

        for rec in recommendations:
            summary_parts.append(
                f"🏷️  {rec.product_name} (x{rec.quantity_needed}): "
                f"{rec.recommended_supplier_name} - "
                f"${rec.unit_price:.2f}/unit (Total: ${rec.total_cost:.2f}, "
                f"{rec.lead_time_days} days) - {rec.reason}"
            )

        summary_message = "\n".join(summary_parts)

        logger.info(f"Generated {len(recommendations)} recommendations")

        return {
            "recommendations": recommendations,
            "summary_message": summary_message
        }

    except Exception as e:
        logger.error(f"Error analyzing quotes: {e}")
        return {
            "recommendations": [],
            "summary_message": f"❌ Error analyzing quotes: {str(e)}"
        }
