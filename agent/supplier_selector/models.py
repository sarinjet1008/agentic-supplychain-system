"""Data models for Supplier Selector Agent."""

from typing import TypedDict, List, Dict, Any
from pydantic import BaseModel


class SupplierQuote(BaseModel):
    """Supplier quote for a specific item."""
    supplier_id: str
    supplier_name: str
    product_id: str
    product_name: str
    unit_price: float
    lead_time_days: int
    min_order_quantity: int
    quantity_needed: int
    total_cost: float


class SupplierRecommendation(BaseModel):
    """Recommended supplier for an item."""
    product_id: str
    product_name: str
    quantity_needed: int
    recommended_supplier_id: str
    recommended_supplier_name: str
    unit_price: float
    total_cost: float
    lead_time_days: int
    reason: str


class SupplierState(TypedDict):
    """State for Supplier Selector workflow."""
    items_to_source: List[Dict[str, Any]]  # Items needing quotes
    supplier_data: Dict[str, Any]  # Loaded supplier catalog
    all_quotes: List[SupplierQuote]  # All quotes collected
    recommendations: List[SupplierRecommendation]  # Best suppliers for each item
    summary_message: str  # Human-readable summary
