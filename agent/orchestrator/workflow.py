"""LangGraph workflow for Orchestrator Agent."""

import logging
from langgraph.graph import StateGraph, END
from agent.orchestrator.models import OrchestratorState
from agent.orchestrator import nodes
from protocols.a2a.router import A2ARouter

logger = logging.getLogger(__name__)


def create_orchestrator_workflow(inventory_workflow, supplier_workflow, po_workflow):
    """
    Create the Orchestrator workflow graph with A2A protocol support.

    Args:
        inventory_workflow: Compiled inventory workflow
        supplier_workflow: Compiled supplier workflow
        po_workflow: Compiled PO workflow

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize A2A Router
    logger.info("Initializing A2A Router for agent communication")
    a2a_router = A2ARouter()

    # Register agent workflows with the router
    a2a_router.register_agent("inventory_monitor", inventory_workflow)
    a2a_router.register_agent("supplier_selector", supplier_workflow)
    a2a_router.register_agent("purchase_order", po_workflow)

    logger.info(f"Registered {len(a2a_router.agent_workflows)} agents with A2A router")

    # Create workflow graph
    workflow = StateGraph(OrchestratorState)

    # Define nodes with A2A router
    workflow.add_node("parse_input", nodes.parse_user_input)
    workflow.add_node(
        "run_inventory",
        lambda state: nodes.run_inventory_check(state, a2a_router)
    )
    workflow.add_node(
        "run_supplier_selection",
        lambda state: nodes.run_supplier_selection(state, a2a_router)
    )
    workflow.add_node(
        "run_po_generation",
        lambda state: nodes.run_po_generation(state, a2a_router)
    )
    workflow.add_node("generate_response", nodes.generate_response)

    # Define conditional routing function
    def route_after_parse(state: OrchestratorState) -> str:
        """Route based on workflow stage after parsing."""
        stage = state.get("workflow_stage", "initial")

        logger.info(f"[route_after_parse] Routing based on stage: '{stage}'")

        if stage == "approved":
            # User approved reorder - proceed with supplier selection
            logger.info("[route_after_parse] -> run_supplier_selection")
            return "run_supplier_selection"
        elif stage == "supplier_approved":
            # User approved all products - proceed with PO generation
            logger.info("[route_after_parse] -> run_po_generation")
            return "run_po_generation"
        elif stage == "rejected":
            # User rejected - go to response
            logger.info("[route_after_parse] -> generate_response (rejected)")
            return "generate_response"
        elif stage in ["awaiting_approval", "awaiting_product_approval"]:
            # Still waiting for user input - go directly to response (re-prompt user)
            logger.info(f"[route_after_parse] -> generate_response ({stage})")
            return "generate_response"
        else:
            # Initial or other - run inventory check
            logger.info("[route_after_parse] -> run_inventory")
            return "run_inventory"

    # Define edges (workflow flow)
    workflow.set_entry_point("parse_input")

    # Conditional routing after parsing
    workflow.add_conditional_edges(
        "parse_input",
        route_after_parse,
        {
            "run_inventory": "run_inventory",
            "run_supplier_selection": "run_supplier_selection",
            "run_po_generation": "run_po_generation",
            "generate_response": "generate_response"
        }
    )
    logger.info("Conditional routing: initial->inventory, approved->supplier, supplier_approved->po, awaiting_product_approval->response")

    # Inventory -> Response (show items, ask for approval)
    workflow.add_edge("run_inventory", "generate_response")

    # Supplier Selection -> Response (show per-product approval - HITL Gate #2)
    workflow.add_edge("run_supplier_selection", "generate_response")

    # PO Generation -> Response (show results)
    workflow.add_edge("run_po_generation", "generate_response")

    # Response -> END
    workflow.add_edge("generate_response", END)

    # Compile the workflow
    compiled_workflow = workflow.compile()

    logger.info("Orchestrator workflow created successfully")

    return compiled_workflow
