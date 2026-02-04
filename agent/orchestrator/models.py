"""State models for Orchestrator Agent."""

from typing import List, Dict, Any, TypedDict, Optional
from models.inventory import ReorderRecommendation


class OrchestratorState(TypedDict):
    """State for Orchestrator workflow."""

    # User interaction
    user_message: str  # User's input message
    conversation_history: List[Dict[str, str]]  # Chat history

    # Conversation state tracking
    workflow_stage: str  # Current stage: 'initial', 'awaiting_approval', 'awaiting_product_approval', 'supplier_approved', 'complete'
    pending_action: str  # Action waiting for approval: 'create_pos', 'none'

    # Inventory results
    reorder_recommendations: List[ReorderRecommendation]  # From inventory agent
    inventory_summary: str  # Summary of inventory check

    # Supplier results
    supplier_recommendations: List[Dict[str, Any]]  # From supplier agent
    supplier_summary: str  # Summary of supplier selection

    # Per-product approval tracking (HITL Gate #2)
    current_product_index: int  # Index of current product being approved
    approved_products: List[Dict[str, Any]]  # Products user has approved

    # PO results
    purchase_orders: List[Dict[str, Any]]  # Generated purchase orders
    po_summary: str  # Summary of PO generation

    # Response to user
    agent_response: str  # Response message to show user
