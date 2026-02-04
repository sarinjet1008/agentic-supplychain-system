"""State models for Inventory Monitor Agent."""

from typing import List, Dict, Any, TypedDict
from models.inventory import InventoryItem, ReorderRecommendation


class InventoryState(TypedDict):
    """State for Inventory Monitor workflow."""

    # Input
    check_all: bool  # Whether to check all items or specific ones

    # Intermediate data
    inventory_data: List[Dict[str, Any]]  # Raw inventory data from CSV
    inventory_items: List[InventoryItem]  # Parsed inventory items

    # Output
    low_stock_items: List[InventoryItem]  # Items below reorder point
    reorder_recommendations: List[ReorderRecommendation]  # Reorder suggestions
    summary_message: str  # Human-readable summary
