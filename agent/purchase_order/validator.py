"""Purchase Order Validator Sub-Agent.

This module implements a validator sub-agent that validates purchase orders
before they are saved. This demonstrates the Deep Agents SDK's sub-agent
spawning capability (via the 'task' tool).

The validator runs validation checks on high-value orders and ensures
business rules are followed.
"""

import logging
from typing import Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from agent.purchase_order.models import PurchaseOrder, POLineItem

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue."""
    severity: ValidationSeverity
    message: str
    field: str = ""


class ValidationResult(BaseModel):
    """Result of a PO validation check.

    Attributes:
        is_valid: Overall validation status
        warnings: List of warning messages (non-blocking)
        errors: List of error messages (blocking)
        issues: List of ValidationIssue objects (structured)
        checks_performed: Number of validation checks performed
        checks_passed: Number of checks that passed
    """
    is_valid: bool = Field(..., description="Whether PO passed all validation checks")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Structured validation issues")
    checks_performed: int = Field(default=0, description="Total checks performed")
    checks_passed: int = Field(default=0, description="Checks passed")


class POValidator:
    """Validates purchase orders against business rules.

    This acts as a sub-agent that can be spawned by the Purchase Order Agent
    to validate orders before saving.
    """

    # Configuration
    HIGH_VALUE_THRESHOLD = 5000.0  # Orders above this trigger manager approval
    MAX_QUANTITY_THRESHOLD = 100  # Large quantity warning
    MAX_ORDER_TOTAL = 50000.0  # Maximum order total allowed
    VALID_SUPPLIERS = ["SUP001", "SUP002", "SUP003"]  # Known suppliers

    def __init__(self):
        """Initialize the validator."""
        self.checks_performed = 0
        self.checks_passed = 0
        logger.info("PO Validator sub-agent initialized")

    def validate_purchase_order(self, po: PurchaseOrder) -> ValidationResult:
        """Validate a purchase order.

        Args:
            po: Purchase order to validate

        Returns:
            ValidationResult with validation status and messages
        """
        logger.info(f"[Validator Sub-Agent] Validating PO: {po.po_number}")

        result = ValidationResult(
            is_valid=True,
            warnings=[],
            errors=[]
        )

        # Run all validation checks
        self._check_high_value(po, result)
        self._check_supplier(po, result)
        self._check_quantities(po, result)
        self._check_line_items(po, result)
        self._check_totals(po, result)
        self._check_maximum_order_value(po, result)

        # Set counts
        result.checks_performed = self.checks_performed
        result.checks_passed = self.checks_passed

        # Determine overall validity (errors make it invalid)
        if result.errors:
            result.is_valid = False
            logger.warning(f"[Validator Sub-Agent] PO {po.po_number} FAILED validation: {len(result.errors)} errors")
        else:
            logger.info(f"[Validator Sub-Agent] PO {po.po_number} PASSED validation")
            if result.warnings:
                logger.info(f"[Validator Sub-Agent] {len(result.warnings)} warnings issued")

        return result

    def _check_high_value(self, po: PurchaseOrder, result: ValidationResult) -> None:
        """Check if order is high-value and requires manager approval."""
        self.checks_performed += 1

        if po.total_amount > self.HIGH_VALUE_THRESHOLD:
            msg = (f"⚠️  High-value order: ${po.total_amount:.2f} exceeds threshold "
                   f"(${self.HIGH_VALUE_THRESHOLD:.2f}) - Requires manager approval")
            result.warnings.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=msg,
                field="total_amount"
            ))
            logger.info(f"High-value order detected: ${po.total_amount:.2f}")
        else:
            self.checks_passed += 1

    def _check_supplier(self, po: PurchaseOrder, result: ValidationResult) -> None:
        """Validate that the supplier is known and approved."""
        self.checks_performed += 1

        if po.supplier_id not in self.VALID_SUPPLIERS:
            msg = (f"❌ Unknown or unapproved supplier: {po.supplier_id}. "
                   f"Valid suppliers: {', '.join(self.VALID_SUPPLIERS)}")
            result.errors.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=msg,
                field="supplier_id"
            ))
            logger.error(f"Invalid supplier: {po.supplier_id}")
        else:
            self.checks_passed += 1
            logger.debug(f"Supplier {po.supplier_id} is valid")

    def _check_quantities(self, po: PurchaseOrder, result: ValidationResult) -> None:
        """Check for unusually large quantities."""
        self.checks_performed += 1
        large_quantities_found = False

        for item in po.line_items:
            if item.quantity > self.MAX_QUANTITY_THRESHOLD:
                msg = (f"⚠️  Large quantity for {item.product_name}: {item.quantity} units "
                       f"(threshold: {self.MAX_QUANTITY_THRESHOLD})")
                result.warnings.append(msg)
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=msg,
                    field="line_items.quantity"
                ))
                large_quantities_found = True
                logger.info(f"Large quantity detected: {item.product_name} x {item.quantity}")

        if not large_quantities_found:
            self.checks_passed += 1

    def _check_line_items(self, po: PurchaseOrder, result: ValidationResult) -> None:
        """Validate line items."""
        self.checks_performed += 1
        errors_before = len(result.errors)

        if not po.line_items:
            msg = "❌ Purchase order has no line items"
            result.errors.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=msg,
                field="line_items"
            ))
            logger.error(f"PO {po.po_number} has no line items")
            return

        # Check each line item
        for idx, item in enumerate(po.line_items, 1):
            # Validate quantities
            if item.quantity <= 0:
                msg = f"❌ Line item {idx} ({item.product_name}): Invalid quantity {item.quantity}"
                result.errors.append(msg)
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=msg,
                    field=f"line_items[{idx}].quantity"
                ))
                logger.error(f"Invalid quantity for {item.product_name}: {item.quantity}")

            # Validate prices
            if item.unit_price <= 0:
                msg = f"❌ Line item {idx} ({item.product_name}): Invalid unit price ${item.unit_price}"
                result.errors.append(msg)
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=msg,
                    field=f"line_items[{idx}].unit_price"
                ))
                logger.error(f"Invalid price for {item.product_name}: ${item.unit_price}")

            # Validate line total
            expected_line_total = item.quantity * item.unit_price
            if abs(item.line_total - expected_line_total) > 0.01:  # Allow small floating point errors
                msg = (f"❌ Line item {idx} ({item.product_name}): Line total mismatch "
                       f"(expected ${expected_line_total:.2f}, got ${item.line_total:.2f})")
                result.errors.append(msg)
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=msg,
                    field=f"line_items[{idx}].line_total"
                ))
                logger.error(f"Subtotal mismatch for {item.product_name}")

        if len(result.errors) == errors_before:
            self.checks_passed += 1

    def _check_totals(self, po: PurchaseOrder, result: ValidationResult) -> None:
        """Validate order totals and tax calculations."""
        self.checks_performed += 1
        errors_before = len(result.errors)

        # Calculate expected values
        expected_subtotal = sum(item.line_total for item in po.line_items)
        expected_tax = expected_subtotal * po.tax_rate
        expected_total = expected_subtotal + expected_tax

        # Allow small floating point differences
        tolerance = 0.01

        if abs(po.subtotal - expected_subtotal) > tolerance:
            msg = f"❌ Subtotal mismatch: expected ${expected_subtotal:.2f}, got ${po.subtotal:.2f}"
            result.errors.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=msg,
                field="subtotal"
            ))
            logger.error(f"Subtotal mismatch in PO {po.po_number}")

        if abs(po.tax_amount - expected_tax) > tolerance:
            msg = f"❌ Tax amount mismatch: expected ${expected_tax:.2f}, got ${po.tax_amount:.2f}"
            result.errors.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=msg,
                field="tax_amount"
            ))
            logger.error(f"Tax calculation error in PO {po.po_number}")

        if abs(po.total_amount - expected_total) > tolerance:
            msg = f"❌ Total amount mismatch: expected ${expected_total:.2f}, got ${po.total_amount:.2f}"
            result.errors.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=msg,
                field="total_amount"
            ))
            logger.error(f"Total calculation error in PO {po.po_number}")

        if len(result.errors) == errors_before:
            self.checks_passed += 1
            logger.debug("All totals validated successfully")

    def _check_maximum_order_value(self, po: PurchaseOrder, result: ValidationResult) -> None:
        """Check if order exceeds maximum allowed value."""
        self.checks_performed += 1

        if po.total_amount > self.MAX_ORDER_TOTAL:
            msg = (f"❌ Order total ${po.total_amount:.2f} exceeds maximum allowed "
                   f"(${self.MAX_ORDER_TOTAL:.2f})")
            result.errors.append(msg)
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=msg,
                field="total_amount"
            ))
            logger.error(f"Order exceeds maximum: ${po.total_amount:.2f}")
        else:
            self.checks_passed += 1


def validate_purchase_order(po: PurchaseOrder) -> ValidationResult:
    """Validate a purchase order (standalone function).

    This is the primary validation function that can be called directly
    with a PurchaseOrder object.

    Args:
        po: Purchase order to validate

    Returns:
        ValidationResult with validation status and messages
    """
    validator = POValidator()
    return validator.validate_purchase_order(po)


def validate_po(po_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a purchase order (function interface for agents).

    This is a convenience function that can be called by agents.

    Args:
        po_dict: Purchase order as dictionary

    Returns:
        ValidationResult as dictionary
    """
    try:
        # Convert dict to PurchaseOrder model
        po = PurchaseOrder(**po_dict)

        # Create validator and run validation
        result = validate_purchase_order(po)

        return result.model_dump()

    except Exception as e:
        logger.error(f"Validation failed with exception: {e}", exc_info=True)
        return {
            "is_valid": False,
            "warnings": [],
            "errors": [f"Validation failed: {str(e)}"],
            "issues": [],
            "checks_performed": 0,
            "checks_passed": 0
        }
