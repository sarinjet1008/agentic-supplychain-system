"""LangGraph workflow for Supplier Selector Agent."""

import logging
from langgraph.graph import StateGraph, END
from agent.supplier_selector.models import SupplierState
from agent.supplier_selector import nodes

logger = logging.getLogger(__name__)


def create_supplier_workflow():
    """
    Create the Supplier Selector workflow graph.

    Workflow:
    1. Load supplier data from JSON
    2. Collect quotes from all suppliers
    3. Analyze and recommend best suppliers

    Returns:
        Compiled LangGraph workflow
    """
    # Create workflow graph
    workflow = StateGraph(SupplierState)

    # Define nodes
    workflow.add_node("load_suppliers", nodes.load_suppliers)
    workflow.add_node("collect_quotes", nodes.collect_quotes)
    workflow.add_node("analyze_and_recommend", nodes.analyze_and_recommend)

    # Define edges (workflow flow)
    workflow.set_entry_point("load_suppliers")
    workflow.add_edge("load_suppliers", "collect_quotes")
    workflow.add_edge("collect_quotes", "analyze_and_recommend")
    workflow.add_edge("analyze_and_recommend", END)

    # Compile the workflow
    compiled_workflow = workflow.compile()

    logger.info("Supplier Selector workflow created successfully")

    return compiled_workflow
