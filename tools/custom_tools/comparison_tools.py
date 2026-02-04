"""Supplier Comparison Tools.

This module provides comparison and ranking utilities for evaluating
suppliers based on various criteria including price, lead time, quality,
and overall value scoring.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ComparisonCriteria(str, Enum):
    """Criteria for supplier comparison."""
    PRICE = "price"
    LEAD_TIME = "lead_time"
    QUALITY = "quality"
    RELIABILITY = "reliability"
    OVERALL = "overall"


class SupplierScore(BaseModel):
    """Scoring result for a supplier."""
    supplier_id: str = Field(..., description="Supplier identifier")
    supplier_name: str = Field(..., description="Supplier name")
    price_score: float = Field(..., description="Price score (0-100, lower price = higher score)")
    lead_time_score: float = Field(..., description="Lead time score (0-100, faster = higher score)")
    quality_score: float = Field(..., description="Quality/rating score (0-100)")
    reliability_score: float = Field(..., description="Reliability score (0-100)")
    overall_score: float = Field(..., description="Weighted overall score (0-100)")
    rank: int = Field(default=0, description="Rank among compared suppliers")
    recommendation: str = Field(default="", description="Recommendation text")


class ComparisonResult(BaseModel):
    """Result of a supplier comparison."""
    product_id: str = Field(..., description="Product being compared")
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(..., description="Quantity needed")
    supplier_scores: List[SupplierScore] = Field(default_factory=list)
    best_supplier: Optional[SupplierScore] = Field(default=None)
    comparison_notes: List[str] = Field(default_factory=list)


@dataclass
class ComparisonWeights:
    """Weights for comparison criteria."""
    price: float = 0.40
    lead_time: float = 0.25
    quality: float = 0.20
    reliability: float = 0.15

    def validate(self) -> bool:
        """Validate that weights sum to 1.0."""
        total = self.price + self.lead_time + self.quality + self.reliability
        return abs(total - 1.0) < 0.001


# Default weights for different scenarios
WEIGHT_PROFILES = {
    "balanced": ComparisonWeights(price=0.35, lead_time=0.25, quality=0.25, reliability=0.15),
    "cost_focused": ComparisonWeights(price=0.60, lead_time=0.15, quality=0.15, reliability=0.10),
    "quality_focused": ComparisonWeights(price=0.20, lead_time=0.15, quality=0.45, reliability=0.20),
    "speed_focused": ComparisonWeights(price=0.25, lead_time=0.50, quality=0.15, reliability=0.10),
    "reliable": ComparisonWeights(price=0.25, lead_time=0.20, quality=0.25, reliability=0.30),
}


def normalize_score(
    value: float,
    min_val: float,
    max_val: float,
    invert: bool = False
) -> float:
    """Normalize a value to 0-100 scale.

    Args:
        value: Value to normalize
        min_val: Minimum possible value
        max_val: Maximum possible value
        invert: If True, lower values get higher scores

    Returns:
        Normalized score (0-100)
    """
    if max_val == min_val:
        return 50.0

    normalized = (value - min_val) / (max_val - min_val)

    if invert:
        normalized = 1 - normalized

    return round(normalized * 100, 2)


def calculate_price_score(
    price: float,
    all_prices: List[float]
) -> float:
    """Calculate price score (lower price = higher score).

    Args:
        price: Supplier's price
        all_prices: All prices being compared

    Returns:
        Price score (0-100)
    """
    if not all_prices:
        return 50.0

    min_price = min(all_prices)
    max_price = max(all_prices)

    return normalize_score(price, min_price, max_price, invert=True)


def calculate_lead_time_score(
    lead_time: int,
    all_lead_times: List[int]
) -> float:
    """Calculate lead time score (faster = higher score).

    Args:
        lead_time: Supplier's lead time in days
        all_lead_times: All lead times being compared

    Returns:
        Lead time score (0-100)
    """
    if not all_lead_times:
        return 50.0

    min_lt = min(all_lead_times)
    max_lt = max(all_lead_times)

    return normalize_score(lead_time, min_lt, max_lt, invert=True)


def calculate_quality_score(rating: float, max_rating: float = 5.0) -> float:
    """Calculate quality score from rating.

    Args:
        rating: Supplier's quality rating
        max_rating: Maximum possible rating

    Returns:
        Quality score (0-100)
    """
    return round((rating / max_rating) * 100, 2)


def calculate_reliability_score(
    on_time_delivery_pct: float = 95.0,
    order_accuracy_pct: float = 98.0
) -> float:
    """Calculate reliability score from delivery and accuracy metrics.

    Args:
        on_time_delivery_pct: Percentage of on-time deliveries
        order_accuracy_pct: Percentage of accurate orders

    Returns:
        Reliability score (0-100)
    """
    # Weighted average of delivery and accuracy
    return round((on_time_delivery_pct * 0.6 + order_accuracy_pct * 0.4), 2)


def score_supplier(
    supplier_id: str,
    supplier_name: str,
    price: float,
    lead_time: int,
    rating: float,
    all_prices: List[float],
    all_lead_times: List[int],
    weights: ComparisonWeights = None,
    reliability_metrics: Optional[Dict[str, float]] = None
) -> SupplierScore:
    """Calculate comprehensive score for a supplier.

    Args:
        supplier_id: Supplier identifier
        supplier_name: Supplier name
        price: Supplier's price for the product
        lead_time: Lead time in days
        rating: Quality rating (0-5)
        all_prices: All prices being compared
        all_lead_times: All lead times being compared
        weights: Optional custom weights
        reliability_metrics: Optional reliability data

    Returns:
        SupplierScore with all scores calculated
    """
    if weights is None:
        weights = WEIGHT_PROFILES["balanced"]

    # Calculate individual scores
    price_score = calculate_price_score(price, all_prices)
    lead_time_score = calculate_lead_time_score(lead_time, all_lead_times)
    quality_score = calculate_quality_score(rating)

    if reliability_metrics:
        reliability_score = calculate_reliability_score(
            reliability_metrics.get("on_time_delivery_pct", 95.0),
            reliability_metrics.get("order_accuracy_pct", 98.0)
        )
    else:
        # Default reliability based on rating
        reliability_score = quality_score * 0.9 + 10

    # Calculate weighted overall score
    overall_score = (
        price_score * weights.price +
        lead_time_score * weights.lead_time +
        quality_score * weights.quality +
        reliability_score * weights.reliability
    )

    return SupplierScore(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        price_score=price_score,
        lead_time_score=lead_time_score,
        quality_score=quality_score,
        reliability_score=reliability_score,
        overall_score=round(overall_score, 2)
    )


def compare_suppliers(
    product_id: str,
    product_name: str,
    quantity: int,
    supplier_quotes: List[Dict[str, Any]],
    weights: ComparisonWeights = None,
    weight_profile: str = "balanced"
) -> ComparisonResult:
    """Compare multiple suppliers for a product.

    Args:
        product_id: Product identifier
        product_name: Product name
        quantity: Quantity needed
        supplier_quotes: List of supplier quote data
        weights: Optional custom weights
        weight_profile: Name of weight profile to use if weights not provided

    Returns:
        ComparisonResult with ranked suppliers
    """
    if weights is None:
        weights = WEIGHT_PROFILES.get(weight_profile, WEIGHT_PROFILES["balanced"])

    logger.info(f"Comparing {len(supplier_quotes)} suppliers for {product_name} (qty: {quantity})")

    # Extract all prices and lead times for normalization
    all_prices = [q.get("unit_price", 0) * quantity for q in supplier_quotes]
    all_lead_times = [q.get("lead_time_days", 0) for q in supplier_quotes]

    # Score each supplier
    scores = []
    for quote in supplier_quotes:
        total_price = quote.get("unit_price", 0) * quantity

        score = score_supplier(
            supplier_id=quote.get("supplier_id", ""),
            supplier_name=quote.get("supplier_name", ""),
            price=total_price,
            lead_time=quote.get("lead_time_days", 0),
            rating=quote.get("rating", 4.0),
            all_prices=all_prices,
            all_lead_times=all_lead_times,
            weights=weights
        )
        scores.append(score)

    # Rank suppliers by overall score
    scores.sort(key=lambda x: x.overall_score, reverse=True)
    for i, score in enumerate(scores):
        score.rank = i + 1

        # Generate recommendation
        if score.rank == 1:
            score.recommendation = "Best overall choice"
        elif score.price_score >= 90:
            score.recommendation = "Best price option"
        elif score.lead_time_score >= 90:
            score.recommendation = "Fastest delivery"
        elif score.quality_score >= 90:
            score.recommendation = "Highest quality"
        else:
            score.recommendation = "Alternative option"

    # Build comparison notes
    notes = []
    if scores:
        best = scores[0]
        notes.append(f"Recommended: {best.supplier_name} (Score: {best.overall_score}/100)")

        # Price comparison
        prices = [(s.supplier_name, all_prices[i]) for i, s in enumerate(scores)]
        cheapest = min(prices, key=lambda x: x[1])
        most_expensive = max(prices, key=lambda x: x[1])
        if cheapest[0] != most_expensive[0]:
            savings = most_expensive[1] - cheapest[1]
            notes.append(f"Price range: ${cheapest[1]:.2f} - ${most_expensive[1]:.2f} (${savings:.2f} savings potential)")

        # Lead time comparison
        lead_times = [(s.supplier_name, all_lead_times[i]) for i, s in enumerate(scores)]
        fastest = min(lead_times, key=lambda x: x[1])
        slowest = max(lead_times, key=lambda x: x[1])
        if fastest[0] != slowest[0]:
            notes.append(f"Lead time: {fastest[1]}-{slowest[1]} days")

    result = ComparisonResult(
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        supplier_scores=scores,
        best_supplier=scores[0] if scores else None,
        comparison_notes=notes
    )

    logger.info(f"Comparison complete. Best: {result.best_supplier.supplier_name if result.best_supplier else 'None'}")
    return result


def compare_by_criteria(
    supplier_quotes: List[Dict[str, Any]],
    criteria: ComparisonCriteria,
    quantity: int = 1
) -> List[Dict[str, Any]]:
    """Compare suppliers by a specific criterion.

    Args:
        supplier_quotes: List of supplier quote data
        criteria: Criterion to compare by
        quantity: Quantity for price calculations

    Returns:
        Sorted list of suppliers with rankings
    """
    ranked = []

    for quote in supplier_quotes:
        entry = {
            "supplier_id": quote.get("supplier_id"),
            "supplier_name": quote.get("supplier_name"),
            "value": 0,
            "rank": 0
        }

        if criteria == ComparisonCriteria.PRICE:
            entry["value"] = quote.get("unit_price", 0) * quantity
            entry["display"] = f"${entry['value']:.2f}"
        elif criteria == ComparisonCriteria.LEAD_TIME:
            entry["value"] = quote.get("lead_time_days", 0)
            entry["display"] = f"{entry['value']} days"
        elif criteria == ComparisonCriteria.QUALITY:
            entry["value"] = quote.get("rating", 0)
            entry["display"] = f"{entry['value']:.1f}/5.0"
        elif criteria == ComparisonCriteria.RELIABILITY:
            entry["value"] = quote.get("on_time_pct", 95)
            entry["display"] = f"{entry['value']:.1f}%"

        ranked.append(entry)

    # Sort (lower is better for price and lead time, higher is better for quality/reliability)
    reverse = criteria in [ComparisonCriteria.QUALITY, ComparisonCriteria.RELIABILITY]
    ranked.sort(key=lambda x: x["value"], reverse=reverse)

    # Assign ranks
    for i, entry in enumerate(ranked):
        entry["rank"] = i + 1

    return ranked


def find_best_value(
    supplier_quotes: List[Dict[str, Any]],
    quantity: int,
    max_lead_time: Optional[int] = None,
    min_rating: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Find the best value supplier with optional constraints.

    Args:
        supplier_quotes: List of supplier quote data
        quantity: Quantity needed
        max_lead_time: Maximum acceptable lead time
        min_rating: Minimum acceptable rating

    Returns:
        Best supplier quote or None if no match
    """
    # Filter by constraints
    filtered = supplier_quotes.copy()

    if max_lead_time is not None:
        filtered = [q for q in filtered if q.get("lead_time_days", 999) <= max_lead_time]

    if min_rating is not None:
        filtered = [q for q in filtered if q.get("rating", 0) >= min_rating]

    if not filtered:
        logger.warning("No suppliers match the given constraints")
        return None

    # Find lowest total cost among filtered
    best = min(filtered, key=lambda q: q.get("unit_price", float('inf')) * quantity)

    logger.info(f"Best value: {best.get('supplier_name')} at ${best.get('unit_price', 0) * quantity:.2f}")
    return best


def generate_comparison_summary(results: List[ComparisonResult]) -> str:
    """Generate a human-readable comparison summary.

    Args:
        results: List of comparison results

    Returns:
        Formatted summary string
    """
    lines = ["📊 Supplier Comparison Summary", "=" * 40]

    for result in results:
        lines.append(f"\n📦 {result.product_name} (Qty: {result.quantity})")
        lines.append("-" * 30)

        for score in result.supplier_scores:
            rank_emoji = "🥇" if score.rank == 1 else "🥈" if score.rank == 2 else "🥉" if score.rank == 3 else f"#{score.rank}"
            lines.append(
                f"{rank_emoji} {score.supplier_name}: Score {score.overall_score}/100"
            )
            lines.append(
                f"   Price: {score.price_score:.0f} | Lead: {score.lead_time_score:.0f} | "
                f"Quality: {score.quality_score:.0f} | Reliable: {score.reliability_score:.0f}"
            )

        if result.comparison_notes:
            lines.append("\n💡 Notes:")
            for note in result.comparison_notes:
                lines.append(f"   • {note}")

    return "\n".join(lines)
