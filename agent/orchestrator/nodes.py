"""Node functions for Orchestrator Agent."""

import logging
from typing import Any, Dict, List
from agent.orchestrator.models import OrchestratorState
from tools.deep_tools.planning_tool import write_todos, format_task_list
from protocols.a2a.message_schemas import A2ARequest, A2AResponse
from protocols.a2a.router import A2ARouter
from agent.base.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit = get_audit_logger()


def parse_user_input(state: OrchestratorState) -> Dict[str, Any]:
    """
    Parse user input and determine action.
    Uses Deep Agents planning tool to generate task breakdown.

    Supports:
    - check inventory / inventory status
    - yes / approve / proceed (approval)
    - no / cancel / reject (rejection)
    - help
    - quit/exit

    Args:
        state: Current workflow state

    Returns:
        Updated state with parsed intent and workflow stage
    """
    user_message = state["user_message"].lower().strip()
    workflow_stage = state.get("workflow_stage", "initial")
    reorder_recs = state.get("reorder_recommendations", [])

    logger.info(f"[parse_user_input] Input: '{user_message}'")
    logger.info(f"[parse_user_input] Current stage: {workflow_stage}")
    logger.info(f"[parse_user_input] Reorder recs count: {len(reorder_recs)}")

    # Handle approval/rejection responses
    approval_keywords = ["yes", "y", "approve", "proceed", "go ahead", "ok", "okay"]
    rejection_keywords = ["no", "n", "cancel", "reject", "stop"]

    if any(keyword in user_message for keyword in approval_keywords):
        logger.info(f"[parse_user_input] Approval keyword detected, checking stage...")
        if workflow_stage == "awaiting_approval":
            logger.info("[parse_user_input] User APPROVED - proceeding to supplier selection")
            return {
                "workflow_stage": "approved",
                "user_message": state["user_message"]
            }
        else:
            logger.warning(f"[parse_user_input] Approval keyword but stage is '{workflow_stage}', not 'awaiting_approval'")

    if any(keyword in user_message for keyword in rejection_keywords):
        if workflow_stage in ["awaiting_approval", "awaiting_supplier_selection"]:
            logger.info("User rejected - cancelling operation")
            return {
                "workflow_stage": "rejected",
                "user_message": state["user_message"]
            }

    # Handle per-product approval responses (HITL Gate #2)
    if workflow_stage == "awaiting_product_approval":
        supplier_recs = state.get("supplier_recommendations", [])
        current_index = state.get("current_product_index", 0)
        approved_products = state.get("approved_products", [])

        # Get current product being asked about
        if current_index < len(supplier_recs):
            current_rec = supplier_recs[current_index]
            product_name = current_rec.get("product_name", "Unknown")

            # Check for approval
            if any(keyword in user_message for keyword in approval_keywords):
                logger.info(f"[parse_user_input] User APPROVED product: {product_name}")
                audit.log_hitl_gate("PRODUCT_APPROVAL", "APPROVED", f"Product: {product_name}")
                approved_products.append(current_rec)
                next_index = current_index + 1

                # Check if more products to approve
                if next_index < len(supplier_recs):
                    return {
                        "workflow_stage": "awaiting_product_approval",
                        "current_product_index": next_index,
                        "approved_products": approved_products,
                        "user_message": state["user_message"]
                    }
                else:
                    # All products processed - proceed to PO generation
                    logger.info(f"[parse_user_input] All products processed. Approved: {len(approved_products)}")
                    audit.log_action("ORCHESTRATOR", "Product selection complete", f"Approved: {len(approved_products)} of {len(supplier_recs)}")
                    return {
                        "workflow_stage": "supplier_approved",
                        "approved_products": approved_products,
                        "supplier_recommendations": approved_products,  # Only approved products
                        "user_message": state["user_message"]
                    }

            # Check for rejection
            if any(keyword in user_message for keyword in rejection_keywords):
                logger.info(f"[parse_user_input] User REJECTED product: {product_name}")
                audit.log_hitl_gate("PRODUCT_APPROVAL", "REJECTED", f"Product: {product_name}")
                next_index = current_index + 1

                # Check if more products to approve
                if next_index < len(supplier_recs):
                    return {
                        "workflow_stage": "awaiting_product_approval",
                        "current_product_index": next_index,
                        "approved_products": approved_products,
                        "user_message": state["user_message"]
                    }
                else:
                    # All products processed
                    if approved_products:
                        logger.info(f"[parse_user_input] All products processed. Approved: {len(approved_products)}")
                        audit.log_action("ORCHESTRATOR", "Product selection complete", f"Approved: {len(approved_products)} of {len(supplier_recs)}")
                        return {
                            "workflow_stage": "supplier_approved",
                            "approved_products": approved_products,
                            "supplier_recommendations": approved_products,
                            "user_message": state["user_message"]
                        }
                    else:
                        # No products approved - cancel workflow
                        logger.info("[parse_user_input] No products approved - cancelling")
                        audit.log_action("ORCHESTRATOR", "Workflow cancelled", "No products approved")
                        return {
                            "workflow_stage": "rejected",
                            "user_message": state["user_message"]
                        }

        # If user typed something else, re-prompt
        logger.info("[parse_user_input] Unrecognized input during product approval - will re-prompt")
        return {
            "workflow_stage": "awaiting_product_approval",
            "current_product_index": current_index,
            "approved_products": approved_products,
            "user_message": state["user_message"]
        }

    # For new requests, use Deep Agents planning tool
    if any(keyword in user_message for keyword in ["check inventory", "inventory", "stock"]):
        logger.info("[Deep Agents] Generating task plan using write_todos")
        task_plan = write_todos("create purchase orders for low stock items")
        task_list_display = format_task_list(task_plan, show_agent=True)
        logger.info(f"[Deep Agents] Generated {len(task_plan)} task steps")
        # Store for potential display to user
        logger.debug(f"\n{task_list_display}")
        # Reset to initial for new inventory check
        return {
            "workflow_stage": "initial",
            "user_message": state["user_message"]
        }

    # If we're awaiting approval and user didn't say yes/no, preserve the stage
    # This allows the user to be re-prompted
    if workflow_stage == "awaiting_approval":
        logger.info("[parse_user_input] Preserving awaiting_approval stage - will re-prompt user")
        return {
            "workflow_stage": "awaiting_approval",
            "user_message": state["user_message"]
        }

    # Default: treat as new inventory check request
    logger.info("[parse_user_input] Default case - treating as new request")
    return {
        "workflow_stage": "initial",
        "user_message": state["user_message"]
    }


def run_inventory_check(state: OrchestratorState, a2a_router: A2ARouter) -> Dict[str, Any]:
    """
    Run the inventory monitor workflow via A2A protocol.

    Args:
        state: Current workflow state
        a2a_router: A2A router for agent communication

    Returns:
        Updated state with inventory results
    """
    logger.info("[A2A] Running inventory check via A2A router...")
    audit.log_a2a_message("orchestrator", "inventory_monitor", "check_inventory")

    try:
        # Create A2A request
        request = A2ARequest(
            method="check_inventory",
            params={
                "check_all": True,
                "inventory_data": [],
                "inventory_items": [],
                "low_stock_items": [],
                "reorder_recommendations": [],
                "summary_message": ""
            },
            source_agent="orchestrator",
            target_agent="inventory_monitor"
        )

        # Route through A2A router
        response = a2a_router.route_message(request)

        if response.error:
            logger.error(f"[A2A] Inventory check failed: {response.error}")
            audit.log_error("INVENTORY_AGENT", response.error.get('message', 'Unknown error'))
            return {
                "reorder_recommendations": [],
                "inventory_summary": f"❌ Error checking inventory: {response.error.get('message', 'Unknown error')}"
            }

        result = response.result
        recs = result.get("reorder_recommendations", [])
        logger.info("[A2A] Inventory check completed successfully via A2A protocol")
        audit.log_action("INVENTORY_AGENT", "Check completed", f"Low stock items: {len(recs)}")

        return {
            "reorder_recommendations": recs,
            "inventory_summary": result.get("summary_message", "")
        }

    except Exception as e:
        logger.error(f"Error during inventory check: {e}")
        audit.log_error("INVENTORY_AGENT", str(e))
        return {
            "reorder_recommendations": [],
            "inventory_summary": f"❌ Error checking inventory: {str(e)}"
        }


def run_supplier_selection(state: OrchestratorState, a2a_router: A2ARouter) -> Dict[str, Any]:
    """
    Run the supplier selector workflow via A2A protocol.

    Args:
        state: Current workflow state
        a2a_router: A2A router for agent communication

    Returns:
        Updated state with supplier recommendations
    """
    logger.info("[A2A] Running supplier selection via A2A router...")

    try:
        reorder_recommendations = state.get("reorder_recommendations", [])

        # Convert reorder recommendations to items_to_source format
        # Handle both Pydantic models and dicts
        items_to_source = []
        for rec in reorder_recommendations:
            if hasattr(rec, 'item'):
                # Pydantic model
                items_to_source.append({
                    "product_id": rec.item.item_id,
                    "product_name": rec.item.name,
                    "quantity_needed": rec.quantity_to_order
                })
            elif isinstance(rec, dict):
                # Dict (serialized)
                item = rec.get("item", {})
                items_to_source.append({
                    "product_id": item.get("item_id", ""),
                    "product_name": item.get("name", ""),
                    "quantity_needed": rec.get("quantity_to_order", 0)
                })

        # Create A2A request
        request = A2ARequest(
            method="select_supplier",
            params={
                "items_to_source": items_to_source,
                "supplier_data": {},
                "all_quotes": [],
                "recommendations": [],
                "summary_message": ""
            },
            source_agent="orchestrator",
            target_agent="supplier_selector"
        )

        # Route through A2A router
        response = a2a_router.route_message(request)

        if response.error:
            logger.error(f"[A2A] Supplier selection failed: {response.error}")
            return {
                "supplier_recommendations": [],
                "supplier_summary": f"❌ Error during supplier selection: {response.error.get('message', 'Unknown error')}"
            }

        result = response.result
        logger.info("[A2A] Supplier selection completed successfully via A2A protocol")

        # Convert Pydantic models to dicts for state storage (handle both dict and Pydantic)
        recommendations = result.get("recommendations", [])
        recommendations_dicts = []
        for rec in recommendations:
            if hasattr(rec, 'model_dump'):
                recommendations_dicts.append(rec.model_dump())
            elif isinstance(rec, dict):
                recommendations_dicts.append(rec)
            else:
                recommendations_dicts.append(dict(rec))

        audit.log_action("SUPPLIER_AGENT", "Recommendations generated", f"Count: {len(recommendations_dicts)}")
        return {
            "supplier_recommendations": recommendations_dicts,
            "supplier_summary": result.get("summary_message", ""),
            "workflow_stage": "awaiting_product_approval",  # HITL Gate #2 - Per-product approval
            "current_product_index": 0,  # Start with first product
            "approved_products": []  # No products approved yet
        }

    except Exception as e:
        logger.error(f"Error during supplier selection: {e}")
        return {
            "supplier_recommendations": [],
            "supplier_summary": f"❌ Error during supplier selection: {str(e)}"
        }


def run_po_generation(state: OrchestratorState, a2a_router: A2ARouter) -> Dict[str, Any]:
    """
    Run the purchase order generation workflow via A2A protocol.

    Args:
        state: Current workflow state
        a2a_router: A2A router for agent communication

    Returns:
        Updated state with PO results
    """
    logger.info("[A2A] Running purchase order generation via A2A router...")
    audit.log_a2a_message("orchestrator", "purchase_order", "generate_purchase_order")

    try:
        # Use approved_products if available, otherwise fall back to supplier_recommendations
        approved_products = state.get("approved_products", [])
        supplier_recommendations = approved_products if approved_products else state.get("supplier_recommendations", [])

        audit.log_action("PO_AGENT", "Starting PO generation", f"Products: {len(supplier_recommendations)}")

        # Create A2A request
        request = A2ARequest(
            method="generate_purchase_order",
            params={
                "recommendations": supplier_recommendations,
                "purchase_orders": [],
                "saved_files": [],
                "summary_message": ""
            },
            source_agent="orchestrator",
            target_agent="purchase_order"
        )

        # Route through A2A router
        response = a2a_router.route_message(request)

        if response.error:
            logger.error(f"[A2A] PO generation failed: {response.error}")
            return {
                "purchase_orders": [],
                "po_summary": f"❌ Error during PO generation: {response.error.get('message', 'Unknown error')}",
                "workflow_stage": "complete"
            }

        result = response.result
        logger.info("[A2A] PO generation completed successfully via A2A protocol")

        # Convert Pydantic models to dicts for state storage (handle both dict and Pydantic)
        purchase_orders = result.get("purchase_orders", [])
        po_dicts = []
        for po in purchase_orders:
            if hasattr(po, 'model_dump'):
                po_dict = po.model_dump()
            elif isinstance(po, dict):
                po_dict = po
            else:
                po_dict = dict(po)
            po_dicts.append(po_dict)

            # Log each PO generated
            audit.log_po_generated(
                po_dict.get("po_number", "Unknown"),
                po_dict.get("supplier_name", "Unknown"),
                po_dict.get("total_amount", 0)
            )

        audit.log_action("PO_AGENT", "Generation complete", f"POs created: {len(po_dicts)}")

        return {
            "purchase_orders": po_dicts,
            "po_summary": result.get("summary_message", ""),
            "workflow_stage": "complete"
        }

    except Exception as e:
        logger.error(f"Error during PO generation: {e}")
        return {
            "purchase_orders": [],
            "po_summary": f"❌ Error during PO generation: {str(e)}",
            "workflow_stage": "complete"
        }


def generate_response(state: OrchestratorState) -> Dict[str, Any]:
    """
    Generate response message for the user.

    Args:
        state: Current workflow state

    Returns:
        Updated state with agent response
    """
    logger.info("Generating response to user...")

    workflow_stage = state.get("workflow_stage", "initial")
    inventory_summary = state.get("inventory_summary", "")
    supplier_summary = state.get("supplier_summary", "")
    po_summary = state.get("po_summary", "")
    reorder_recommendations = state.get("reorder_recommendations", [])

    # Build response based on workflow stage
    if workflow_stage == "rejected":
        agent_response = "Operation cancelled. Type 'check inventory' to start a new check."
        new_stage = "initial"

    elif workflow_stage == "complete":
        # Show full results: supplier selection + PO generation
        response_parts = []
        if supplier_summary:
            response_parts.append("📊 **Supplier Selection Results:**")
            response_parts.append(supplier_summary)
            response_parts.append("")
        if po_summary:
            response_parts.append("📋 **Purchase Order Generation:**")
            response_parts.append(po_summary)

        if not response_parts:
            response_parts.append("Workflow completed but no details available.")

        agent_response = "\n".join(response_parts)
        new_stage = "initial"

    elif workflow_stage == "awaiting_product_approval":
        # HITL Gate #2: Per-product approval - ask about one product at a time
        supplier_recommendations = state.get("supplier_recommendations", [])
        current_index = state.get("current_product_index", 0)
        approved_products = state.get("approved_products", [])
        response_parts = []

        # Show summary on first product only
        if current_index == 0 and supplier_summary:
            response_parts.append("📊 **Supplier Analysis Complete:**")
            response_parts.append(supplier_summary)
            response_parts.append("")

        # Show progress if not first product
        if current_index > 0:
            response_parts.append(f"📋 Progress: {current_index} of {len(supplier_recommendations)} products reviewed")
            response_parts.append(f"✅ Approved so far: {len(approved_products)}")
            response_parts.append("")

        # Show current product for approval
        if current_index < len(supplier_recommendations):
            rec = supplier_recommendations[current_index]
            product_name = rec.get("product_name", "Unknown")
            product_id = rec.get("product_id", "")
            supplier_name = rec.get("recommended_supplier_name", "Unknown")
            unit_price = rec.get("unit_price", 0)
            total_cost = rec.get("total_cost", 0)
            lead_time = rec.get("lead_time_days", 0)
            quantity = rec.get("quantity_needed", 0)
            reason = rec.get("reason", "")

            response_parts.append(f"🛒 **Product {current_index + 1} of {len(supplier_recommendations)}:**")
            response_parts.append("")
            response_parts.append(f"   📦 **{product_name}** (#{product_id})")
            response_parts.append(f"   📊 Quantity: {quantity} units")
            response_parts.append(f"   🏪 Supplier: {supplier_name}")
            response_parts.append(f"   💰 Price: ${unit_price:.2f}/unit")
            response_parts.append(f"   💵 **Total: ${total_cost:.2f}**")
            response_parts.append(f"   🚚 Delivery: {lead_time} days")
            if reason:
                response_parts.append(f"   ℹ️  {reason}")
            response_parts.append("")
            response_parts.append(f"🤔 **Order {product_name} from {supplier_name}?** (yes/no)")

        agent_response = "\n".join(response_parts)
        new_stage = "awaiting_product_approval"  # Stay in this stage

    elif workflow_stage == "awaiting_approval":
        # Re-prompt user for approval (they typed something that wasn't yes/no)
        response_parts = []

        # Show summary of items needing reorder (construct from recommendations if inventory_summary is empty)
        if inventory_summary:
            response_parts.append(inventory_summary)
        elif reorder_recommendations:
            response_parts.append(f"📦 Items needing reorder ({len(reorder_recommendations)} items):")
            for rec in reorder_recommendations[:5]:  # Show first 5
                if hasattr(rec, 'item'):
                    item = rec.item
                    response_parts.append(f"  • {item.name}: {item.current_stock} in stock (reorder at {item.reorder_point})")
                elif isinstance(rec, dict):
                    item = rec.get('item', {})
                    response_parts.append(f"  • {item.get('name', 'Unknown')}: {item.get('current_stock', 0)} in stock")

        response_parts.append("\n⏳ **Awaiting your approval.** Please type 'yes' to proceed with purchase orders or 'no' to cancel.")
        agent_response = "\n".join(response_parts)
        new_stage = "awaiting_approval"  # Stay in this stage

    elif workflow_stage == "initial":
        # Show inventory check results
        response_parts = [inventory_summary]

        if reorder_recommendations:
            response_parts.append("\nWould you like me to help you create purchase orders for these items? (yes/no)")
            new_stage = "awaiting_approval"
        else:
            new_stage = "initial"

        agent_response = "\n".join(response_parts)

    else:
        agent_response = "Processing..."
        new_stage = workflow_stage

    logger.info(f"Response generated (stage: {workflow_stage} -> {new_stage})")

    return {
        "agent_response": agent_response,
        "workflow_stage": new_stage,
        "pending_action": "create_pos" if new_stage == "awaiting_approval" else "none"
    }
