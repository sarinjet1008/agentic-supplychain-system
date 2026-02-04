"""Data models for Purchase Order Agent."""

from typing import TypedDict, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class POLineItem(BaseModel):
    """Line item in a purchase order."""
    line_number: int
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    line_total: float


class PurchaseOrder(BaseModel):
    """Complete purchase order document."""
    po_number: str
    date_created: str
    supplier_id: str
    supplier_name: str
    supplier_contact: str
    line_items: List[POLineItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    notes: str


class POState(TypedDict, total=False):
    """State for Purchase Order workflow."""
    recommendations: List[Dict[str, Any]]  # Supplier recommendations
    purchase_orders: List[PurchaseOrder]  # Generated PO documents
    saved_files: List[str]  # Paths to saved PO files
    summary_message: str  # Human-readable summary
    validation_warnings: List[str]  # Validation warnings from PO validator sub-agent
    validation_errors: List[str]  # Validation errors from PO validator sub-agent
