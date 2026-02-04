"""Business Rule Validation Tools.

This module provides validation utilities for business rules including
purchase order validation, supplier validation, inventory validation,
and approval workflow validation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(str, Enum):
    """Categories of validation rules."""
    BUSINESS_RULE = "business_rule"
    DATA_INTEGRITY = "data_integrity"
    COMPLIANCE = "compliance"
    THRESHOLD = "threshold"
    APPROVAL = "approval"


class ValidationResult(BaseModel):
    """Result of a single validation check."""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    category: ValidationCategory = Field(..., description="Validation category")
    severity: ValidationSeverity = Field(..., description="Severity level")
    passed: bool = Field(..., description="Whether validation passed")
    message: str = Field(..., description="Result message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional details")


class ValidationReport(BaseModel):
    """Complete validation report."""
    entity_type: str = Field(..., description="Type of entity validated (e.g., 'purchase_order')")
    entity_id: str = Field(..., description="Entity identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    is_valid: bool = Field(..., description="Overall validation status")
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    results: List[ValidationResult] = Field(default_factory=list)
    requires_approval: bool = Field(default=False, description="Whether HITL approval is required")
    approval_reasons: List[str] = Field(default_factory=list)


@dataclass
class ValidationRule:
    """Definition of a validation rule."""
    rule_id: str
    rule_name: str
    category: ValidationCategory
    severity: ValidationSeverity
    validator: Callable[[Dict[str, Any]], Tuple[bool, str, Optional[Dict[str, Any]]]]
    enabled: bool = True


# Business rule thresholds
THRESHOLDS = {
    "max_po_value": 50000.00,
    "high_value_po": 10000.00,
    "max_line_items": 100,
    "max_quantity_per_item": 10000,
    "min_order_value": 10.00,
    "max_lead_time_days": 90,
    "min_supplier_rating": 3.0,
    "max_single_supplier_pct": 80.0,  # Max % of order to single supplier
}

# Approved suppliers list
APPROVED_SUPPLIERS = ["SUP001", "SUP002", "SUP003"]


def validate_po_value(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate purchase order value limits."""
    total = data.get("total_amount", 0)
    max_value = THRESHOLDS["max_po_value"]

    if total > max_value:
        return (
            False,
            f"PO value ${total:.2f} exceeds maximum allowed ${max_value:.2f}",
            {"total": total, "max_allowed": max_value}
        )

    return (True, f"PO value ${total:.2f} is within limits", {"total": total})


def validate_high_value_approval(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Check if high-value PO needs approval."""
    total = data.get("total_amount", 0)
    threshold = THRESHOLDS["high_value_po"]

    if total > threshold:
        return (
            False,
            f"High-value PO (${total:.2f}) requires manager approval (threshold: ${threshold:.2f})",
            {"total": total, "threshold": threshold, "requires_approval": True}
        )

    return (True, f"PO value ${total:.2f} does not require special approval", {"total": total})


def validate_supplier_approved(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate that supplier is on approved list."""
    supplier_id = data.get("supplier_id", "")

    if supplier_id not in APPROVED_SUPPLIERS:
        return (
            False,
            f"Supplier {supplier_id} is not on the approved suppliers list",
            {"supplier_id": supplier_id, "approved_list": APPROVED_SUPPLIERS}
        )

    return (True, f"Supplier {supplier_id} is approved", {"supplier_id": supplier_id})


def validate_line_items_count(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate number of line items."""
    line_items = data.get("line_items", [])
    count = len(line_items)
    max_items = THRESHOLDS["max_line_items"]

    if count > max_items:
        return (
            False,
            f"Too many line items ({count}). Maximum allowed: {max_items}",
            {"count": count, "max_allowed": max_items}
        )

    if count == 0:
        return (
            False,
            "PO must have at least one line item",
            {"count": 0}
        )

    return (True, f"Line items count ({count}) is valid", {"count": count})


def validate_quantities(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate item quantities."""
    line_items = data.get("line_items", [])
    max_qty = THRESHOLDS["max_quantity_per_item"]
    issues = []

    for item in line_items:
        qty = item.get("quantity", 0)
        if qty <= 0:
            issues.append(f"{item.get('product_name', 'Unknown')}: quantity must be positive")
        elif qty > max_qty:
            issues.append(f"{item.get('product_name', 'Unknown')}: quantity {qty} exceeds max {max_qty}")

    if issues:
        return (
            False,
            f"Quantity validation failed: {'; '.join(issues)}",
            {"issues": issues}
        )

    return (True, "All quantities are valid", {"item_count": len(line_items)})


def validate_line_totals(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate that line totals match calculations."""
    line_items = data.get("line_items", [])
    issues = []

    for item in line_items:
        qty = item.get("quantity", 0)
        price = item.get("unit_price", 0)
        line_total = item.get("line_total", 0)
        expected = qty * price

        if abs(line_total - expected) > 0.01:
            issues.append(
                f"{item.get('product_name', 'Unknown')}: line_total ${line_total:.2f} "
                f"doesn't match {qty} x ${price:.2f} = ${expected:.2f}"
            )

    if issues:
        return (
            False,
            f"Line total calculation errors: {'; '.join(issues)}",
            {"issues": issues}
        )

    return (True, "All line totals are correct", {"verified_items": len(line_items)})


def validate_tax_calculation(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate tax calculation accuracy."""
    subtotal = data.get("subtotal", 0)
    tax_rate = data.get("tax_rate", 0.08)
    tax_amount = data.get("tax_amount", 0)
    total = data.get("total_amount", 0)

    expected_tax = round(subtotal * tax_rate, 2)
    expected_total = round(subtotal + expected_tax, 2)

    issues = []
    if abs(tax_amount - expected_tax) > 0.01:
        issues.append(f"Tax amount ${tax_amount:.2f} doesn't match expected ${expected_tax:.2f}")

    if abs(total - expected_total) > 0.01:
        issues.append(f"Total ${total:.2f} doesn't match expected ${expected_total:.2f}")

    if issues:
        return (
            False,
            f"Tax calculation errors: {'; '.join(issues)}",
            {"subtotal": subtotal, "expected_tax": expected_tax, "expected_total": expected_total}
        )

    return (
        True,
        f"Tax calculation verified: ${subtotal:.2f} + ${tax_amount:.2f} = ${total:.2f}",
        {"tax_rate": tax_rate}
    )


def validate_minimum_order(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate minimum order value."""
    total = data.get("total_amount", 0)
    min_value = THRESHOLDS["min_order_value"]

    if total < min_value:
        return (
            False,
            f"Order total ${total:.2f} is below minimum ${min_value:.2f}",
            {"total": total, "minimum": min_value}
        )

    return (True, f"Order total ${total:.2f} meets minimum requirement", {"total": total})


def validate_supplier_rating(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate supplier meets minimum rating."""
    rating = data.get("supplier_rating", 5.0)
    min_rating = THRESHOLDS["min_supplier_rating"]

    if rating < min_rating:
        return (
            False,
            f"Supplier rating {rating:.1f} is below minimum required {min_rating:.1f}",
            {"rating": rating, "min_required": min_rating, "requires_approval": True}
        )

    return (True, f"Supplier rating {rating:.1f} meets requirements", {"rating": rating})


def validate_lead_time(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate lead time is acceptable."""
    lead_time = data.get("lead_time_days", 0)
    max_lead_time = THRESHOLDS["max_lead_time_days"]

    if lead_time > max_lead_time:
        return (
            False,
            f"Lead time {lead_time} days exceeds maximum {max_lead_time} days",
            {"lead_time": lead_time, "max_allowed": max_lead_time}
        )

    return (True, f"Lead time {lead_time} days is acceptable", {"lead_time": lead_time})


def validate_po_date(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate PO date is valid."""
    date_str = data.get("date_created", "")

    try:
        if date_str:
            po_date = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if po_date < today:
                return (
                    False,
                    f"PO date {date_str} is in the past",
                    {"po_date": date_str, "today": today.strftime("%Y-%m-%d")}
                )
    except ValueError:
        return (
            False,
            f"Invalid date format: {date_str}",
            {"date_str": date_str, "expected_format": "YYYY-MM-DD"}
        )

    return (True, f"PO date {date_str} is valid", {"date": date_str})


def validate_duplicate_items(data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Check for duplicate product IDs in line items."""
    line_items = data.get("line_items", [])
    product_ids = [item.get("product_id") for item in line_items]
    duplicates = [pid for pid in product_ids if product_ids.count(pid) > 1]

    if duplicates:
        unique_duplicates = list(set(duplicates))
        return (
            False,
            f"Duplicate products found: {', '.join(unique_duplicates)}",
            {"duplicates": unique_duplicates}
        )

    return (True, "No duplicate products", {"unique_products": len(set(product_ids))})


# Define all PO validation rules
PO_VALIDATION_RULES: List[ValidationRule] = [
    ValidationRule(
        rule_id="PO001",
        rule_name="Maximum PO Value",
        category=ValidationCategory.THRESHOLD,
        severity=ValidationSeverity.ERROR,
        validator=validate_po_value
    ),
    ValidationRule(
        rule_id="PO002",
        rule_name="High Value Approval",
        category=ValidationCategory.APPROVAL,
        severity=ValidationSeverity.WARNING,
        validator=validate_high_value_approval
    ),
    ValidationRule(
        rule_id="PO003",
        rule_name="Approved Supplier",
        category=ValidationCategory.COMPLIANCE,
        severity=ValidationSeverity.ERROR,
        validator=validate_supplier_approved
    ),
    ValidationRule(
        rule_id="PO004",
        rule_name="Line Items Count",
        category=ValidationCategory.DATA_INTEGRITY,
        severity=ValidationSeverity.ERROR,
        validator=validate_line_items_count
    ),
    ValidationRule(
        rule_id="PO005",
        rule_name="Quantity Validation",
        category=ValidationCategory.DATA_INTEGRITY,
        severity=ValidationSeverity.ERROR,
        validator=validate_quantities
    ),
    ValidationRule(
        rule_id="PO006",
        rule_name="Line Total Accuracy",
        category=ValidationCategory.DATA_INTEGRITY,
        severity=ValidationSeverity.ERROR,
        validator=validate_line_totals
    ),
    ValidationRule(
        rule_id="PO007",
        rule_name="Tax Calculation",
        category=ValidationCategory.DATA_INTEGRITY,
        severity=ValidationSeverity.ERROR,
        validator=validate_tax_calculation
    ),
    ValidationRule(
        rule_id="PO008",
        rule_name="Minimum Order Value",
        category=ValidationCategory.BUSINESS_RULE,
        severity=ValidationSeverity.WARNING,
        validator=validate_minimum_order
    ),
    ValidationRule(
        rule_id="PO009",
        rule_name="Duplicate Items",
        category=ValidationCategory.DATA_INTEGRITY,
        severity=ValidationSeverity.WARNING,
        validator=validate_duplicate_items
    ),
]


def validate_purchase_order(po_data: Dict[str, Any]) -> ValidationReport:
    """Run all validation rules against a purchase order.

    Args:
        po_data: Purchase order data dictionary

    Returns:
        ValidationReport with all results
    """
    po_number = po_data.get("po_number", "UNKNOWN")
    logger.info(f"Validating purchase order: {po_number}")

    results = []
    error_count = 0
    warning_count = 0
    requires_approval = False
    approval_reasons = []

    for rule in PO_VALIDATION_RULES:
        if not rule.enabled:
            continue

        try:
            passed, message, details = rule.validator(po_data)

            result = ValidationResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                category=rule.category,
                severity=rule.severity,
                passed=passed,
                message=message,
                details=details
            )
            results.append(result)

            if not passed:
                if rule.severity == ValidationSeverity.ERROR:
                    error_count += 1
                elif rule.severity == ValidationSeverity.WARNING:
                    warning_count += 1

                # Check if approval is required
                if details and details.get("requires_approval"):
                    requires_approval = True
                    approval_reasons.append(message)

            logger.debug(f"Rule {rule.rule_id}: {'PASS' if passed else 'FAIL'} - {message}")

        except Exception as e:
            logger.error(f"Error running rule {rule.rule_id}: {e}")
            results.append(ValidationResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                category=rule.category,
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Validation error: {str(e)}",
                details={"exception": str(e)}
            ))
            error_count += 1

    is_valid = error_count == 0

    report = ValidationReport(
        entity_type="purchase_order",
        entity_id=po_number,
        is_valid=is_valid,
        error_count=error_count,
        warning_count=warning_count,
        results=results,
        requires_approval=requires_approval,
        approval_reasons=approval_reasons
    )

    logger.info(
        f"Validation complete for {po_number}: "
        f"{'VALID' if is_valid else 'INVALID'} "
        f"(errors: {error_count}, warnings: {warning_count})"
    )

    return report


def validate_inventory_item(item_data: Dict[str, Any]) -> ValidationReport:
    """Validate inventory item data.

    Args:
        item_data: Inventory item data dictionary

    Returns:
        ValidationReport with results
    """
    item_id = item_data.get("item_id", "UNKNOWN")
    results = []
    error_count = 0

    # Check required fields
    required_fields = ["item_id", "name", "current_stock", "reorder_point", "max_stock"]
    for field in required_fields:
        if field not in item_data:
            results.append(ValidationResult(
                rule_id="INV001",
                rule_name="Required Field",
                category=ValidationCategory.DATA_INTEGRITY,
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Missing required field: {field}",
                details={"field": field}
            ))
            error_count += 1

    # Validate stock levels
    current = item_data.get("current_stock", 0)
    reorder = item_data.get("reorder_point", 0)
    max_stock = item_data.get("max_stock", 0)

    if current < 0:
        results.append(ValidationResult(
            rule_id="INV002",
            rule_name="Positive Stock",
            category=ValidationCategory.DATA_INTEGRITY,
            severity=ValidationSeverity.ERROR,
            passed=False,
            message=f"Stock level cannot be negative: {current}",
            details={"current_stock": current}
        ))
        error_count += 1
    else:
        results.append(ValidationResult(
            rule_id="INV002",
            rule_name="Positive Stock",
            category=ValidationCategory.DATA_INTEGRITY,
            severity=ValidationSeverity.INFO,
            passed=True,
            message="Stock level is valid",
            details={"current_stock": current}
        ))

    if reorder > max_stock:
        results.append(ValidationResult(
            rule_id="INV003",
            rule_name="Reorder Point Logic",
            category=ValidationCategory.BUSINESS_RULE,
            severity=ValidationSeverity.WARNING,
            passed=False,
            message=f"Reorder point ({reorder}) exceeds max stock ({max_stock})",
            details={"reorder_point": reorder, "max_stock": max_stock}
        ))

    return ValidationReport(
        entity_type="inventory_item",
        entity_id=item_id,
        is_valid=error_count == 0,
        error_count=error_count,
        warning_count=len([r for r in results if not r.passed and r.severity == ValidationSeverity.WARNING]),
        results=results
    )


def format_validation_report(report: ValidationReport) -> str:
    """Format a validation report for display.

    Args:
        report: ValidationReport to format

    Returns:
        Formatted string representation
    """
    lines = [
        f"{'='*50}",
        f"Validation Report: {report.entity_type.upper()}",
        f"ID: {report.entity_id}",
        f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'='*50}",
        "",
        f"Status: {'✅ VALID' if report.is_valid else '❌ INVALID'}",
        f"Errors: {report.error_count} | Warnings: {report.warning_count}",
    ]

    if report.requires_approval:
        lines.append(f"\n⚠️  REQUIRES APPROVAL:")
        for reason in report.approval_reasons:
            lines.append(f"   • {reason}")

    lines.append("\nDetails:")
    lines.append("-" * 50)

    for result in report.results:
        icon = "✅" if result.passed else "❌" if result.severity == ValidationSeverity.ERROR else "⚠️"
        lines.append(f"{icon} [{result.rule_id}] {result.rule_name}")
        lines.append(f"   {result.message}")

    return "\n".join(lines)


def quick_validate(po_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """Quick validation returning simple results.

    Args:
        po_data: Purchase order data

    Returns:
        Tuple of (is_valid, error_messages, warning_messages)
    """
    report = validate_purchase_order(po_data)

    errors = [r.message for r in report.results if not r.passed and r.severity == ValidationSeverity.ERROR]
    warnings = [r.message for r in report.results if not r.passed and r.severity == ValidationSeverity.WARNING]

    return (report.is_valid, errors, warnings)
