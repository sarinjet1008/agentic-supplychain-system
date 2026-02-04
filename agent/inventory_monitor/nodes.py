"""Node functions for Inventory Monitor Agent."""

import logging
from typing import Any, Dict
from models.inventory import InventoryItem, ReorderRecommendation
from agent.inventory_monitor.models import InventoryState

logger = logging.getLogger(__name__)


def load_inventory_data(state: InventoryState, mcp_server) -> Dict[str, Any]:
    """
    Load inventory data from CSV file via MCP server.

    Args:
        state: Current workflow state
        mcp_server: Filesystem MCP server instance

    Returns:
        Updated state with inventory data
    """
    logger.info("Loading inventory data from CSV...")

    try:
        # Read inventory CSV
        inventory_data = mcp_server.read_csv("inventory.csv")
        logger.info(f"Loaded {len(inventory_data)} inventory items")

        # Parse into InventoryItem objects
        inventory_items = [
            InventoryItem(
                item_id=str(row["item_id"]),
                name=row["name"],
                category=row["category"],
                current_stock=int(row["current_stock"]),
                reorder_point=int(row["reorder_point"]),
                unit_cost=float(row["unit_cost"])
            )
            for row in inventory_data
        ]

        return {
            "inventory_data": inventory_data,
            "inventory_items": inventory_items
        }

    except Exception as e:
        logger.error(f"Error loading inventory data: {e}")
        raise


def check_stock_levels(state: InventoryState) -> Dict[str, Any]:
    """
    Check stock levels and identify items needing reorder.

    Args:
        state: Current workflow state with inventory items

    Returns:
        Updated state with low stock items
    """
    logger.info("Checking stock levels...")

    inventory_items = state["inventory_items"]

    # Find items below reorder point
    low_stock_items = [
        item for item in inventory_items
        if item.needs_reorder
    ]

    logger.info(f"Found {len(low_stock_items)} items below reorder point")

    return {
        "low_stock_items": low_stock_items
    }


def generate_recommendations(state: InventoryState) -> Dict[str, Any]:
    """
    Generate reorder recommendations for low stock items.

    Args:
        state: Current workflow state with low stock items

    Returns:
        Updated state with recommendations and summary
    """
    logger.info("Generating reorder recommendations...")

    low_stock_items = state["low_stock_items"]

    if not low_stock_items:
        summary = "✅ All items are adequately stocked. No reorders needed."
        return {
            "reorder_recommendations": [],
            "summary_message": summary
        }

    # Generate recommendations
    recommendations = []
    for item in low_stock_items:
        # Simple recommendation: order enough to reach reorder point
        quantity_to_order = item.quantity_needed

        # Determine priority based on how far below reorder point
        shortage_pct = (item.reorder_point - item.current_stock) / item.reorder_point
        if shortage_pct > 0.5:
            priority = "high"
        elif shortage_pct > 0.3:
            priority = "normal"
        else:
            priority = "low"

        recommendation = ReorderRecommendation(
            item=item,
            quantity_to_order=quantity_to_order,
            reason=f"Current stock ({item.current_stock}) below reorder point ({item.reorder_point})",
            priority=priority
        )
        recommendations.append(recommendation)

    # Create summary message
    summary_lines = [
        f"\n⚠️  Found {len(low_stock_items)} item(s) that need reordering:\n"
    ]

    for rec in recommendations:
        item = rec.item
        priority_emoji = "🔴" if rec.priority == "high" else "🟡"
        summary_lines.append(
            f"{priority_emoji} {item.name} (#{item.item_id}): "
            f"{item.current_stock} units in stock (reorder at {item.reorder_point})"
        )

    summary = "\n".join(summary_lines)

    logger.info(f"Generated {len(recommendations)} reorder recommendations")

    return {
        "reorder_recommendations": recommendations,
        "summary_message": summary
    }
