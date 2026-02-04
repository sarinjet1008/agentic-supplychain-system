"""Domain models for inventory management."""

from typing import Optional
from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    """Represents an inventory item."""

    item_id: str = Field(description="Unique identifier for the item")
    name: str = Field(description="Item name")
    category: str = Field(description="Item category")
    current_stock: int = Field(description="Current stock level")
    reorder_point: int = Field(description="Minimum stock level before reorder")
    unit_cost: float = Field(description="Cost per unit")

    @property
    def needs_reorder(self) -> bool:
        """Check if item needs to be reordered."""
        return self.current_stock < self.reorder_point

    @property
    def quantity_needed(self) -> int:
        """Calculate quantity needed to reach reorder point."""
        if self.needs_reorder:
            return self.reorder_point - self.current_stock
        return 0


class ReorderRecommendation(BaseModel):
    """Represents a reorder recommendation for an item."""

    item: InventoryItem = Field(description="The inventory item")
    quantity_to_order: int = Field(description="Recommended quantity to order")
    reason: str = Field(description="Reason for reorder recommendation")
    priority: str = Field(
        default="normal",
        description="Priority level: low, normal, high, critical"
    )
