"""Node functions for Purchase Order Agent."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
from agent.purchase_order.models import POState, PurchaseOrder, POLineItem
from agent.purchase_order.validator import POValidator

logger = logging.getLogger(__name__)


def generate_po_documents(state: POState) -> Dict[str, Any]:
    """
    Generate purchase order documents from supplier recommendations.

    Groups items by supplier and creates one PO per supplier.

    Args:
        state: Current workflow state

    Returns:
        Updated state with generated POs
    """
    logger.info("Generating purchase order documents...")

    recommendations = state["recommendations"]
    purchase_orders: List[PurchaseOrder] = []

    try:
        # Group recommendations by supplier
        items_by_supplier: Dict[str, List[Dict[str, Any]]] = {}
        for rec in recommendations:
            supplier_id = rec["recommended_supplier_id"]
            if supplier_id not in items_by_supplier:
                items_by_supplier[supplier_id] = []
            items_by_supplier[supplier_id].append(rec)

        # Generate PO for each supplier
        po_counter = 1
        for supplier_id, items in items_by_supplier.items():
            # Get supplier info from first item
            first_item = items[0]
            supplier_name = first_item["recommended_supplier_name"]

            # Load supplier contact info
            supplier_contact = _get_supplier_contact(supplier_id)

            # Create line items
            line_items: List[POLineItem] = []
            for idx, item in enumerate(items, start=1):
                line_item = POLineItem(
                    line_number=idx,
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    quantity=item["quantity_needed"],
                    unit_price=item["unit_price"],
                    line_total=item["total_cost"]
                )
                line_items.append(line_item)

            # Calculate totals
            subtotal = sum(item.line_total for item in line_items)
            tax_rate = 0.08  # 8% tax rate
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount

            # Generate PO number
            date_str = datetime.now().strftime("%Y%m%d")
            po_number = f"PO-{date_str}-{po_counter:03d}"

            # Create PO document
            po = PurchaseOrder(
                po_number=po_number,
                date_created=datetime.now().isoformat(),
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                supplier_contact=supplier_contact,
                line_items=line_items,
                subtotal=subtotal,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                total_amount=total_amount,
                notes="Auto-generated purchase order from inventory monitoring system"
            )

            purchase_orders.append(po)
            po_counter += 1

        logger.info(f"Generated {len(purchase_orders)} purchase order(s)")

        # Validate POs using validator sub-agent (Deep Agents SDK sub-agent pattern)
        validation_warnings = []
        validation_errors = []

        logger.info("[Sub-Agent] Spawning PO Validator sub-agent for validation...")
        validator = POValidator()

        for po in purchase_orders:
            logger.info(f"[Sub-Agent] Validating {po.po_number} (${po.total_amount:.2f})...")
            validation_result = validator.validate_purchase_order(po)

            if validation_result.warnings:
                validation_warnings.extend([f"{po.po_number}: {w}" for w in validation_result.warnings])

            if validation_result.errors:
                validation_errors.extend([f"{po.po_number}: {e}" for e in validation_result.errors])

            logger.info(
                f"[Sub-Agent] Validation complete: "
                f"{'PASSED' if validation_result.is_valid else 'FAILED'} "
                f"({validation_result.checks_passed}/{validation_result.checks_performed} checks)"
            )

        # Log validation summary
        if validation_errors:
            logger.error(f"[Sub-Agent] Validation found {len(validation_errors)} errors")
            for error in validation_errors:
                logger.error(f"  - {error}")
        elif validation_warnings:
            logger.warning(f"[Sub-Agent] Validation found {len(validation_warnings)} warnings")
            for warning in validation_warnings:
                logger.warning(f"  - {warning}")
        else:
            logger.info("[Sub-Agent] All POs passed validation with no warnings")

        return {
            "purchase_orders": purchase_orders,
            "validation_warnings": validation_warnings,
            "validation_errors": validation_errors
        }

    except Exception as e:
        logger.error(f"Error generating PO documents: {e}")
        return {
            "purchase_orders": [],
            "summary_message": f"❌ Error generating PO documents: {str(e)}"
        }


def save_po_files(state: POState) -> Dict[str, Any]:
    """
    Save purchase order documents to filesystem.

    Args:
        state: Current workflow state

    Returns:
        Updated state with file paths and summary
    """
    logger.info("Saving purchase order files...")

    purchase_orders = state["purchase_orders"]
    saved_files: List[str] = []

    try:
        # Ensure output directory exists
        output_dir = Path("data/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save each PO
        for po in purchase_orders:
            # Create filename
            filename = f"{po.po_number}.json"
            file_path = output_dir / filename

            # Convert PO to dict and save as JSON
            po_dict = po.model_dump()

            with open(file_path, 'w') as f:
                json.dump(po_dict, f, indent=2)

            saved_files.append(str(file_path))
            logger.info(f"Saved PO to {file_path}")

        # Get validation results from state
        validation_warnings = state.get("validation_warnings", [])
        validation_errors = state.get("validation_errors", [])

        # Generate summary message
        summary_parts = [f"✅ Purchase Order Generation Complete!\n"]

        for po in purchase_orders:
            item_count = len(po.line_items)
            summary_parts.append(
                f"📄 {po.po_number}:\n"
                f"   Supplier: {po.supplier_name}\n"
                f"   Items: {item_count}\n"
                f"   Subtotal: ${po.subtotal:.2f}\n"
                f"   Tax (8%): ${po.tax_amount:.2f}\n"
                f"   Total: ${po.total_amount:.2f}"
            )

        # Add validation results
        if validation_errors:
            summary_parts.append(f"\n❌ Validation Errors ({len(validation_errors)}):")
            for error in validation_errors[:3]:  # Show first 3
                summary_parts.append(f"   {error}")
        elif validation_warnings:
            summary_parts.append(f"\n⚠️  Validation Warnings ({len(validation_warnings)}):")
            for warning in validation_warnings[:3]:  # Show first 3
                summary_parts.append(f"   {warning}")
        else:
            summary_parts.append("\n✅ All purchase orders passed validation")

        summary_parts.append(f"\n💾 Saved {len(saved_files)} file(s) to: {output_dir}")

        summary_message = "\n".join(summary_parts)

        logger.info(f"Saved {len(saved_files)} PO file(s)")

        return {
            "saved_files": saved_files,
            "summary_message": summary_message
        }

    except Exception as e:
        logger.error(f"Error saving PO files: {e}")
        return {
            "saved_files": [],
            "summary_message": f"❌ Error saving PO files: {str(e)}"
        }


def _get_supplier_contact(supplier_id: str) -> str:
    """
    Helper function to get supplier contact information.

    Args:
        supplier_id: Supplier ID

    Returns:
        Supplier contact info
    """
    try:
        supplier_file = Path("data/suppliers.json")
        with open(supplier_file, 'r') as f:
            supplier_data = json.load(f)

        for supplier in supplier_data["suppliers"]:
            if supplier["id"] == supplier_id:
                return f"{supplier['contact']} | {supplier['phone']}"

        return "Contact information not available"

    except Exception as e:
        logger.warning(f"Could not load supplier contact: {e}")
        return "Contact information not available"
