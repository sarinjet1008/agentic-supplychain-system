"""Custom Tools Package.

This package provides custom business logic tools for the PO Assistant:

- calculation_tools: Tax calculations, order totals, reorder quantities
- comparison_tools: Supplier comparison and scoring
- validation_tools: Business rule validation for POs and inventory
"""

from tools.custom_tools.calculation_tools import (
    # Models
    TaxCalculation,
    ReorderCalculation,
    CostAnalysis,
    # Functions
    calculate_tax,
    calculate_line_total,
    calculate_order_subtotal,
    calculate_reorder_quantity,
    calculate_shipping_cost,
    calculate_total_landed_cost,
    calculate_bulk_discount,
    calculate_delivery_date,
    calculate_po_totals,
    quick_price_check,
    # Constants
    TAX_RATES,
    SHIPPING_TIERS,
)

from tools.custom_tools.comparison_tools import (
    # Enums
    ComparisonCriteria,
    # Models
    SupplierScore,
    ComparisonResult,
    ComparisonWeights,
    # Functions
    normalize_score,
    calculate_price_score,
    calculate_lead_time_score,
    calculate_quality_score,
    calculate_reliability_score,
    score_supplier,
    compare_suppliers,
    compare_by_criteria,
    find_best_value,
    generate_comparison_summary,
    # Constants
    WEIGHT_PROFILES,
)

from tools.custom_tools.validation_tools import (
    # Enums
    ValidationSeverity,
    ValidationCategory,
    # Models
    ValidationResult,
    ValidationReport,
    ValidationRule,
    # Functions
    validate_purchase_order,
    validate_inventory_item,
    format_validation_report,
    quick_validate,
    # Constants
    THRESHOLDS,
    APPROVED_SUPPLIERS,
    PO_VALIDATION_RULES,
)

__all__ = [
    # Calculation Tools
    "TaxCalculation",
    "ReorderCalculation",
    "CostAnalysis",
    "calculate_tax",
    "calculate_line_total",
    "calculate_order_subtotal",
    "calculate_reorder_quantity",
    "calculate_shipping_cost",
    "calculate_total_landed_cost",
    "calculate_bulk_discount",
    "calculate_delivery_date",
    "calculate_po_totals",
    "quick_price_check",
    "TAX_RATES",
    "SHIPPING_TIERS",
    # Comparison Tools
    "ComparisonCriteria",
    "SupplierScore",
    "ComparisonResult",
    "ComparisonWeights",
    "normalize_score",
    "calculate_price_score",
    "calculate_lead_time_score",
    "calculate_quality_score",
    "calculate_reliability_score",
    "score_supplier",
    "compare_suppliers",
    "compare_by_criteria",
    "find_best_value",
    "generate_comparison_summary",
    "WEIGHT_PROFILES",
    # Validation Tools
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationResult",
    "ValidationReport",
    "ValidationRule",
    "validate_purchase_order",
    "validate_inventory_item",
    "format_validation_report",
    "quick_validate",
    "THRESHOLDS",
    "APPROVED_SUPPLIERS",
    "PO_VALIDATION_RULES",
]
