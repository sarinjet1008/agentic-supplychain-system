"""LangGraph workflow for Purchase Order Agent."""

import logging
from langgraph.graph import StateGraph, END
from agent.purchase_order.models import POState
from agent.purchase_order import nodes

logger = logging.getLogger(__name__)


def create_po_workflow():
    """
    Create the Purchase Order workflow graph.

    Workflow:
    1. Generate PO documents from recommendations
    2. Save PO files to filesystem

    Returns:
        Compiled LangGraph workflow
    """
    # Create workflow graph
    workflow = StateGraph(POState)

    # Define nodes
    workflow.add_node("generate_po_documents", nodes.generate_po_documents)
    workflow.add_node("save_po_files", nodes.save_po_files)

    # Define edges (workflow flow)
    workflow.set_entry_point("generate_po_documents")
    workflow.add_edge("generate_po_documents", "save_po_files")
    workflow.add_edge("save_po_files", END)

    # Compile the workflow
    compiled_workflow = workflow.compile()

    logger.info("Purchase Order workflow created successfully")

    return compiled_workflow
