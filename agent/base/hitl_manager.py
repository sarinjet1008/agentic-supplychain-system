"""Human-in-the-Loop (HITL) Manager.

This module provides a centralized manager for handling all HITL approval gates
in the PO Assistant workflow. It supports multiple gate types and provides
a consistent interface for requesting and processing human approvals.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HITLGateType(str, Enum):
    """Types of HITL approval gates."""
    PO_CREATION = "po_creation"
    SUPPLIER_SELECTION = "supplier_selection"
    HIGH_VALUE_APPROVAL = "high_value_approval"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"
    EXCEPTION_HANDLING = "exception_handling"


class HITLStatus(str, Enum):
    """Status of an HITL request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class HITLOption(BaseModel):
    """An option presented to the user in an HITL gate."""
    id: str = Field(..., description="Option identifier")
    label: str = Field(..., description="Display label")
    description: Optional[str] = Field(default=None, description="Detailed description")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Associated data")
    is_recommended: bool = Field(default=False, description="Whether this is the recommended option")


class HITLRequest(BaseModel):
    """Request for human approval."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    gate_type: HITLGateType
    title: str
    message: str
    options: List[HITLOption] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    timeout_seconds: int = Field(default=300)
    allow_custom_input: bool = Field(default=False)
    require_reason: bool = Field(default=False)


class HITLResponse(BaseModel):
    """Response from human approval."""
    request_id: str
    status: HITLStatus
    selected_option: Optional[str] = None
    custom_input: Optional[str] = None
    reason: Optional[str] = None
    modified_data: Optional[Dict[str, Any]] = None
    responded_at: datetime = Field(default_factory=datetime.now)


class HITLManager:
    """Manager for Human-in-the-Loop approval gates."""

    def __init__(self):
        self.pending_requests: Dict[str, HITLRequest] = {}
        self.responses: Dict[str, HITLResponse] = {}
        self.gate_configs: Dict[HITLGateType, Dict[str, Any]] = self._default_configs()

    def _default_configs(self) -> Dict[HITLGateType, Dict[str, Any]]:
        """Get default configurations for each gate type."""
        return {
            HITLGateType.PO_CREATION: {
                "enabled": True,
                "timeout_seconds": 300,
                "default_options": ["approve", "reject"],
            },
            HITLGateType.SUPPLIER_SELECTION: {
                "enabled": True,
                "timeout_seconds": 300,
                "allow_custom": True,
            },
            HITLGateType.HIGH_VALUE_APPROVAL: {
                "enabled": True,
                "timeout_seconds": 600,
                "threshold": 10000.00,
                "require_reason": True,
            },
            HITLGateType.THRESHOLD_ADJUSTMENT: {
                "enabled": True,
                "timeout_seconds": 300,
                "require_reason": True,
            },
            HITLGateType.EXCEPTION_HANDLING: {
                "enabled": True,
                "timeout_seconds": 300,
                "allow_custom": True,
            },
        }

    def is_gate_enabled(self, gate_type: HITLGateType) -> bool:
        """Check if a gate is enabled."""
        config = self.gate_configs.get(gate_type, {})
        return config.get("enabled", True)

    def create_po_creation_request(
        self,
        items_to_order: List[Dict[str, Any]]
    ) -> HITLRequest:
        """Create HITL request for PO creation approval (Gate #1).

        Args:
            items_to_order: List of items that need purchase orders

        Returns:
            HITLRequest for user approval
        """
        # Build summary of items
        item_lines = []
        for item in items_to_order:
            item_lines.append(
                f"  - {item.get('product_name', 'Unknown')}: "
                f"{item.get('quantity', 0)} units"
            )

        message = f"The following items need to be ordered:\n" + "\n".join(item_lines)
        message += "\n\nWould you like to create purchase orders for these items?"

        request = HITLRequest(
            gate_type=HITLGateType.PO_CREATION,
            title="Create Purchase Orders",
            message=message,
            options=[
                HITLOption(
                    id="approve",
                    label="Yes, create POs",
                    description="Proceed with creating purchase orders",
                    is_recommended=True
                ),
                HITLOption(
                    id="reject",
                    label="No, cancel",
                    description="Cancel the operation"
                ),
            ],
            data={"items": items_to_order}
        )

        self.pending_requests[request.request_id] = request
        logger.info(f"[HITL Gate #1] Created PO creation request: {request.request_id}")
        return request

    def create_supplier_selection_request(
        self,
        product_name: str,
        supplier_options: List[Dict[str, Any]],
        recommended_supplier_id: Optional[str] = None
    ) -> HITLRequest:
        """Create HITL request for supplier selection (Gate #2).

        Args:
            product_name: Name of the product
            supplier_options: List of supplier options with pricing
            recommended_supplier_id: ID of the recommended supplier

        Returns:
            HITLRequest for user selection
        """
        options = []
        for supplier in supplier_options:
            is_recommended = supplier.get("supplier_id") == recommended_supplier_id
            label = f"{supplier.get('supplier_name', 'Unknown')}"
            if is_recommended:
                label += " (Recommended)"

            options.append(HITLOption(
                id=supplier.get("supplier_id", ""),
                label=label,
                description=(
                    f"${supplier.get('unit_price', 0):.2f}/unit, "
                    f"{supplier.get('lead_time_days', 0)} days lead time"
                ),
                data=supplier,
                is_recommended=is_recommended
            ))

        message = f"Please select a supplier for {product_name}:"

        request = HITLRequest(
            gate_type=HITLGateType.SUPPLIER_SELECTION,
            title=f"Select Supplier: {product_name}",
            message=message,
            options=options,
            data={"product_name": product_name, "suppliers": supplier_options},
            allow_custom_input=False
        )

        self.pending_requests[request.request_id] = request
        logger.info(f"[HITL Gate #2] Created supplier selection request: {request.request_id}")
        return request

    def create_high_value_approval_request(
        self,
        po_number: str,
        total_amount: float,
        supplier_name: str,
        line_items: List[Dict[str, Any]]
    ) -> HITLRequest:
        """Create HITL request for high-value PO approval (Gate #3).

        Args:
            po_number: Purchase order number
            total_amount: Total PO value
            supplier_name: Name of the supplier
            line_items: List of line items in the PO

        Returns:
            HITLRequest for manager approval
        """
        threshold = self.gate_configs[HITLGateType.HIGH_VALUE_APPROVAL]["threshold"]

        item_summary = "\n".join([
            f"  - {item.get('product_name', 'Unknown')}: "
            f"{item.get('quantity', 0)} x ${item.get('unit_price', 0):.2f}"
            for item in line_items
        ])

        message = (
            f"**High-Value Purchase Order Approval Required**\n\n"
            f"PO Number: {po_number}\n"
            f"Supplier: {supplier_name}\n"
            f"Total Amount: ${total_amount:,.2f}\n"
            f"Threshold: ${threshold:,.2f}\n\n"
            f"Line Items:\n{item_summary}\n\n"
            f"This order exceeds the approval threshold and requires manager authorization."
        )

        request = HITLRequest(
            gate_type=HITLGateType.HIGH_VALUE_APPROVAL,
            title=f"High-Value PO Approval: {po_number}",
            message=message,
            options=[
                HITLOption(
                    id="approve",
                    label="Approve",
                    description="Authorize this purchase order"
                ),
                HITLOption(
                    id="reject",
                    label="Reject",
                    description="Reject this purchase order"
                ),
                HITLOption(
                    id="modify",
                    label="Request Modification",
                    description="Request changes before approval"
                ),
            ],
            data={
                "po_number": po_number,
                "total_amount": total_amount,
                "supplier_name": supplier_name,
                "line_items": line_items,
                "threshold": threshold
            },
            require_reason=True
        )

        self.pending_requests[request.request_id] = request
        logger.info(f"[HITL Gate #3] Created high-value approval request: {request.request_id}")
        return request

    def create_threshold_adjustment_request(
        self,
        product_id: str,
        product_name: str,
        current_reorder_point: int,
        suggested_reorder_point: int,
        reason: str
    ) -> HITLRequest:
        """Create HITL request for threshold adjustment (Gate #4).

        Args:
            product_id: Product identifier
            product_name: Product name
            current_reorder_point: Current reorder point setting
            suggested_reorder_point: Suggested new reorder point
            reason: Reason for the suggested change

        Returns:
            HITLRequest for user approval
        """
        message = (
            f"**Reorder Threshold Adjustment**\n\n"
            f"Product: {product_name} ({product_id})\n"
            f"Current Reorder Point: {current_reorder_point} units\n"
            f"Suggested Reorder Point: {suggested_reorder_point} units\n\n"
            f"Reason: {reason}\n\n"
            f"Would you like to apply this change?"
        )

        request = HITLRequest(
            gate_type=HITLGateType.THRESHOLD_ADJUSTMENT,
            title=f"Adjust Threshold: {product_name}",
            message=message,
            options=[
                HITLOption(
                    id="approve",
                    label="Apply Change",
                    description=f"Set reorder point to {suggested_reorder_point}"
                ),
                HITLOption(
                    id="reject",
                    label="Keep Current",
                    description=f"Keep reorder point at {current_reorder_point}"
                ),
                HITLOption(
                    id="custom",
                    label="Set Custom Value",
                    description="Enter a different reorder point"
                ),
            ],
            data={
                "product_id": product_id,
                "product_name": product_name,
                "current_value": current_reorder_point,
                "suggested_value": suggested_reorder_point
            },
            allow_custom_input=True,
            require_reason=True
        )

        self.pending_requests[request.request_id] = request
        logger.info(f"[HITL Gate #4] Created threshold adjustment request: {request.request_id}")
        return request

    def create_exception_handling_request(
        self,
        exception_type: str,
        exception_message: str,
        context: Dict[str, Any],
        suggested_actions: List[Dict[str, str]]
    ) -> HITLRequest:
        """Create HITL request for exception handling (Gate #5).

        Args:
            exception_type: Type of exception
            exception_message: Error message
            context: Context information about the error
            suggested_actions: List of suggested actions to handle the exception

        Returns:
            HITLRequest for user decision
        """
        context_str = "\n".join([f"  - {k}: {v}" for k, v in context.items()])

        message = (
            f"**Exception Handling Required**\n\n"
            f"Type: {exception_type}\n"
            f"Message: {exception_message}\n\n"
            f"Context:\n{context_str}\n\n"
            f"Please select how to proceed:"
        )

        options = [
            HITLOption(
                id=action.get("id", f"action_{i}"),
                label=action.get("label", "Unknown Action"),
                description=action.get("description", "")
            )
            for i, action in enumerate(suggested_actions)
        ]

        # Add default options if none provided
        if not options:
            options = [
                HITLOption(id="retry", label="Retry", description="Retry the failed operation"),
                HITLOption(id="skip", label="Skip", description="Skip this item and continue"),
                HITLOption(id="abort", label="Abort", description="Abort the entire workflow"),
            ]

        request = HITLRequest(
            gate_type=HITLGateType.EXCEPTION_HANDLING,
            title=f"Handle Exception: {exception_type}",
            message=message,
            options=options,
            data={
                "exception_type": exception_type,
                "exception_message": exception_message,
                "context": context
            },
            allow_custom_input=True
        )

        self.pending_requests[request.request_id] = request
        logger.info(f"[HITL Gate #5] Created exception handling request: {request.request_id}")
        return request

    def process_response(
        self,
        request_id: str,
        user_input: str,
        reason: Optional[str] = None
    ) -> HITLResponse:
        """Process user response to an HITL request.

        Args:
            request_id: ID of the request being responded to
            user_input: User's input/selection
            reason: Optional reason for the decision

        Returns:
            HITLResponse with processed result
        """
        if request_id not in self.pending_requests:
            logger.error(f"Request {request_id} not found")
            return HITLResponse(
                request_id=request_id,
                status=HITLStatus.CANCELLED,
                reason="Request not found"
            )

        request = self.pending_requests[request_id]

        # Parse user input
        user_input_lower = user_input.lower().strip()

        # Check for approval keywords
        if any(word in user_input_lower for word in ["yes", "y", "approve", "ok", "proceed"]):
            status = HITLStatus.APPROVED
            selected_option = "approve"

        # Check for rejection keywords
        elif any(word in user_input_lower for word in ["no", "n", "reject", "cancel", "stop"]):
            status = HITLStatus.REJECTED
            selected_option = "reject"

        # Check if input matches an option ID
        else:
            matching_option = None
            for option in request.options:
                if (option.id.lower() == user_input_lower or
                    option.label.lower() == user_input_lower or
                    user_input_lower in option.label.lower()):
                    matching_option = option
                    break

            if matching_option:
                selected_option = matching_option.id
                if matching_option.id in ["approve", "yes"]:
                    status = HITLStatus.APPROVED
                elif matching_option.id in ["reject", "no", "cancel"]:
                    status = HITLStatus.REJECTED
                elif matching_option.id in ["modify", "custom"]:
                    status = HITLStatus.MODIFIED
                else:
                    status = HITLStatus.APPROVED  # Selection counts as approval
            else:
                # Custom input
                if request.allow_custom_input:
                    status = HITLStatus.MODIFIED
                    selected_option = "custom"
                else:
                    status = HITLStatus.PENDING
                    selected_option = None

        response = HITLResponse(
            request_id=request_id,
            status=status,
            selected_option=selected_option,
            custom_input=user_input if selected_option == "custom" else None,
            reason=reason
        )

        # Store response and remove from pending
        self.responses[request_id] = response
        del self.pending_requests[request_id]

        logger.info(f"[HITL] Processed response for {request_id}: {status.value}")
        return response

    def format_request_for_display(self, request: HITLRequest) -> str:
        """Format an HITL request for CLI display.

        Args:
            request: HITLRequest to format

        Returns:
            Formatted string for display
        """
        lines = [
            f"\n{'='*50}",
            f"🔔 {request.title}",
            f"{'='*50}",
            "",
            request.message,
            ""
        ]

        if request.options:
            lines.append("Options:")
            for i, option in enumerate(request.options, 1):
                prefix = "👉 " if option.is_recommended else "   "
                lines.append(f"{prefix}{i}. {option.label}")
                if option.description:
                    lines.append(f"      {option.description}")

        lines.append("")
        lines.append("Enter your choice (or type your response):")

        return "\n".join(lines)

    def get_pending_requests(self) -> List[HITLRequest]:
        """Get all pending HITL requests."""
        return list(self.pending_requests.values())

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request.

        Args:
            request_id: ID of the request to cancel

        Returns:
            True if cancelled, False if not found
        """
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
            self.responses[request_id] = HITLResponse(
                request_id=request_id,
                status=HITLStatus.CANCELLED,
                reason="Cancelled by user"
            )
            logger.info(f"[HITL] Cancelled request {request_id}")
            return True
        return False

    def check_high_value_threshold(self, amount: float) -> bool:
        """Check if an amount exceeds the high-value threshold.

        Args:
            amount: Amount to check

        Returns:
            True if amount exceeds threshold
        """
        threshold = self.gate_configs[HITLGateType.HIGH_VALUE_APPROVAL]["threshold"]
        return amount > threshold


# Global HITL manager instance
_hitl_manager: Optional[HITLManager] = None


def get_hitl_manager() -> HITLManager:
    """Get the global HITL manager instance."""
    global _hitl_manager
    if _hitl_manager is None:
        _hitl_manager = HITLManager()
    return _hitl_manager
