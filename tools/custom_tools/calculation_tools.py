"""Business Logic Calculation Tools.

This module provides calculation utilities for business logic operations
in the supply chain workflow, including tax calculations, order totals,
reorder quantities, and cost analysis.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TaxCalculation(BaseModel):
    """Result of a tax calculation."""
    subtotal: float = Field(..., description="Pre-tax subtotal")
    tax_rate: float = Field(..., description="Tax rate as decimal (e.g., 0.08 for 8%)")
    tax_amount: float = Field(..., description="Calculated tax amount")
    total: float = Field(..., description="Total including tax")


class ReorderCalculation(BaseModel):
    """Result of reorder quantity calculation."""
    product_id: str = Field(..., description="Product identifier")
    current_stock: int = Field(..., description="Current stock level")
    reorder_point: int = Field(..., description="Reorder trigger point")
    max_stock: int = Field(..., description="Maximum stock level")
    quantity_to_order: int = Field(..., description="Recommended order quantity")
    safety_stock: int = Field(..., description="Safety stock buffer")
    days_of_stock: float = Field(..., description="Estimated days of remaining stock")


class CostAnalysis(BaseModel):
    """Cost analysis for a purchase decision."""
    product_id: str = Field(..., description="Product identifier")
    supplier_id: str = Field(..., description="Supplier identifier")
    unit_price: float = Field(..., description="Price per unit")
    quantity: int = Field(..., description="Order quantity")
    subtotal: float = Field(..., description="Quantity * unit price")
    shipping_cost: float = Field(..., description="Estimated shipping")
    tax_amount: float = Field(..., description="Tax amount")
    total_cost: float = Field(..., description="Total landed cost")
    cost_per_unit: float = Field(..., description="Total cost / quantity")


# Default tax rates by region
TAX_RATES = {
    "default": 0.08,
    "CA": 0.0725,  # California
    "NY": 0.08,    # New York
    "TX": 0.0625,  # Texas
    "FL": 0.06,    # Florida
    "WA": 0.065,   # Washington
}

# Shipping cost tiers
SHIPPING_TIERS = [
    {"max_weight": 5, "cost": 10.00},
    {"max_weight": 20, "cost": 25.00},
    {"max_weight": 50, "cost": 45.00},
    {"max_weight": 100, "cost": 75.00},
    {"max_weight": float('inf'), "cost": 120.00},
]


def calculate_tax(
    subtotal: float,
    tax_rate: Optional[float] = None,
    region: Optional[str] = None
) -> TaxCalculation:
    """Calculate tax for an order.

    Args:
        subtotal: Pre-tax order total
        tax_rate: Optional explicit tax rate (overrides region)
        region: Optional region code for looking up tax rate

    Returns:
        TaxCalculation with computed values
    """
    # Determine tax rate
    if tax_rate is None:
        if region and region in TAX_RATES:
            tax_rate = TAX_RATES[region]
        else:
            tax_rate = TAX_RATES["default"]

    # Use Decimal for precision
    subtotal_d = Decimal(str(subtotal))
    rate_d = Decimal(str(tax_rate))

    tax_amount_d = (subtotal_d * rate_d).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_d = subtotal_d + tax_amount_d

    result = TaxCalculation(
        subtotal=float(subtotal_d),
        tax_rate=float(rate_d),
        tax_amount=float(tax_amount_d),
        total=float(total_d)
    )

    logger.debug(f"Tax calculated: ${subtotal:.2f} + ${result.tax_amount:.2f} = ${result.total:.2f}")
    return result


def calculate_line_total(
    unit_price: float,
    quantity: int,
    discount_percent: float = 0.0
) -> float:
    """Calculate line item total with optional discount.

    Args:
        unit_price: Price per unit
        quantity: Number of units
        discount_percent: Discount percentage (0-100)

    Returns:
        Line total after discount
    """
    subtotal = Decimal(str(unit_price)) * Decimal(quantity)

    if discount_percent > 0:
        discount = subtotal * (Decimal(str(discount_percent)) / Decimal('100'))
        subtotal = subtotal - discount

    result = float(subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    logger.debug(f"Line total: {quantity} x ${unit_price:.2f} = ${result:.2f}")
    return result


def calculate_order_subtotal(line_items: List[Dict[str, Any]]) -> float:
    """Calculate order subtotal from line items.

    Args:
        line_items: List of items with 'line_total' or 'unit_price' and 'quantity'

    Returns:
        Order subtotal
    """
    total = Decimal('0.00')

    for item in line_items:
        if 'line_total' in item:
            total += Decimal(str(item['line_total']))
        elif 'unit_price' in item and 'quantity' in item:
            total += Decimal(str(item['unit_price'])) * Decimal(item['quantity'])

    result = float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    logger.debug(f"Order subtotal: ${result:.2f} from {len(line_items)} line items")
    return result


def calculate_reorder_quantity(
    product_id: str,
    current_stock: int,
    reorder_point: int,
    max_stock: int,
    avg_daily_usage: float = 1.0,
    safety_stock_days: int = 7,
    lead_time_days: int = 5
) -> ReorderCalculation:
    """Calculate optimal reorder quantity using EOQ-like logic.

    Args:
        product_id: Product identifier
        current_stock: Current stock level
        reorder_point: Level that triggers reorder
        max_stock: Maximum stock level to maintain
        avg_daily_usage: Average units used per day
        safety_stock_days: Days of safety stock to maintain
        lead_time_days: Supplier lead time in days

    Returns:
        ReorderCalculation with recommended quantity
    """
    # Calculate safety stock
    safety_stock = int(avg_daily_usage * safety_stock_days)

    # Days of stock remaining
    days_of_stock = current_stock / avg_daily_usage if avg_daily_usage > 0 else float('inf')

    # Calculate quantity to order
    if current_stock <= reorder_point:
        # Need to order: bring up to max stock plus cover lead time
        quantity_to_order = max_stock - current_stock + int(avg_daily_usage * lead_time_days)
    else:
        quantity_to_order = 0

    # Ensure minimum order quantity
    quantity_to_order = max(0, quantity_to_order)

    result = ReorderCalculation(
        product_id=product_id,
        current_stock=current_stock,
        reorder_point=reorder_point,
        max_stock=max_stock,
        quantity_to_order=quantity_to_order,
        safety_stock=safety_stock,
        days_of_stock=round(days_of_stock, 1)
    )

    logger.debug(f"Reorder calculation for {product_id}: order {quantity_to_order} units")
    return result


def calculate_shipping_cost(
    weight_kg: float,
    expedited: bool = False
) -> float:
    """Estimate shipping cost based on weight.

    Args:
        weight_kg: Total weight in kilograms
        expedited: Whether to use expedited shipping (2x cost)

    Returns:
        Estimated shipping cost
    """
    cost = 0.0

    for tier in SHIPPING_TIERS:
        if weight_kg <= tier['max_weight']:
            cost = tier['cost']
            break

    if expedited:
        cost *= 2

    logger.debug(f"Shipping cost for {weight_kg}kg: ${cost:.2f}")
    return cost


def calculate_total_landed_cost(
    unit_price: float,
    quantity: int,
    shipping_cost: float,
    tax_rate: float = 0.08,
    duties_percent: float = 0.0
) -> CostAnalysis:
    """Calculate total landed cost including all fees.

    Args:
        unit_price: Price per unit
        quantity: Order quantity
        shipping_cost: Shipping cost
        tax_rate: Tax rate as decimal
        duties_percent: Import duties as percentage (0-100)

    Returns:
        CostAnalysis with all cost components
    """
    subtotal = Decimal(str(unit_price)) * Decimal(quantity)

    # Calculate duties if applicable
    duties = subtotal * (Decimal(str(duties_percent)) / Decimal('100'))

    # Taxable amount includes subtotal + shipping + duties
    taxable = subtotal + Decimal(str(shipping_cost)) + duties
    tax_amount = taxable * Decimal(str(tax_rate))

    total_cost = subtotal + Decimal(str(shipping_cost)) + duties + tax_amount
    cost_per_unit = total_cost / Decimal(quantity)

    return CostAnalysis(
        product_id="",  # To be filled by caller
        supplier_id="",  # To be filled by caller
        unit_price=unit_price,
        quantity=quantity,
        subtotal=float(subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        shipping_cost=shipping_cost,
        tax_amount=float(tax_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        total_cost=float(total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        cost_per_unit=float(cost_per_unit.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    )


def calculate_bulk_discount(
    unit_price: float,
    quantity: int,
    discount_tiers: Optional[List[Dict[str, Any]]] = None
) -> Tuple[float, float]:
    """Calculate bulk discount based on quantity.

    Args:
        unit_price: Base unit price
        quantity: Order quantity
        discount_tiers: Optional custom discount tiers

    Returns:
        Tuple of (discounted_unit_price, discount_percentage)
    """
    if discount_tiers is None:
        # Default discount tiers
        discount_tiers = [
            {"min_qty": 100, "discount_pct": 15},
            {"min_qty": 50, "discount_pct": 10},
            {"min_qty": 25, "discount_pct": 5},
            {"min_qty": 10, "discount_pct": 2},
        ]

    # Sort by min_qty descending to find highest applicable discount
    sorted_tiers = sorted(discount_tiers, key=lambda x: x['min_qty'], reverse=True)

    discount_pct = 0.0
    for tier in sorted_tiers:
        if quantity >= tier['min_qty']:
            discount_pct = tier['discount_pct']
            break

    discounted_price = unit_price * (1 - discount_pct / 100)

    logger.debug(f"Bulk discount: qty={quantity}, discount={discount_pct}%, price=${discounted_price:.2f}")
    return round(discounted_price, 2), discount_pct


def calculate_delivery_date(
    lead_time_days: int,
    order_date: Optional[datetime] = None,
    exclude_weekends: bool = True
) -> datetime:
    """Calculate expected delivery date.

    Args:
        lead_time_days: Supplier lead time in days
        order_date: Order date (defaults to now)
        exclude_weekends: Whether to skip weekends in calculation

    Returns:
        Expected delivery datetime
    """
    if order_date is None:
        order_date = datetime.now()

    delivery_date = order_date
    days_added = 0

    while days_added < lead_time_days:
        delivery_date += timedelta(days=1)

        # Skip weekends if requested
        if exclude_weekends and delivery_date.weekday() >= 5:
            continue

        days_added += 1

    logger.debug(f"Delivery date: {delivery_date.strftime('%Y-%m-%d')} (lead time: {lead_time_days} days)")
    return delivery_date


def calculate_po_totals(line_items: List[Dict[str, Any]], tax_rate: float = 0.08) -> Dict[str, float]:
    """Calculate all totals for a purchase order.

    Args:
        line_items: List of line items with quantity and unit_price
        tax_rate: Tax rate as decimal

    Returns:
        Dictionary with subtotal, tax_amount, and total
    """
    subtotal = calculate_order_subtotal(line_items)
    tax_calc = calculate_tax(subtotal, tax_rate)

    return {
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_calc.tax_amount,
        "total": tax_calc.total
    }


# Convenience function for common use case
def quick_price_check(
    unit_price: float,
    quantity: int,
    tax_rate: float = 0.08
) -> Dict[str, float]:
    """Quick calculation of total price with tax.

    Args:
        unit_price: Price per unit
        quantity: Number of units
        tax_rate: Tax rate as decimal

    Returns:
        Dictionary with subtotal, tax, and total
    """
    subtotal = unit_price * quantity
    tax = calculate_tax(subtotal, tax_rate)

    return {
        "unit_price": unit_price,
        "quantity": quantity,
        "subtotal": tax.subtotal,
        "tax_rate": tax.tax_rate,
        "tax_amount": tax.tax_amount,
        "total": tax.total
    }
