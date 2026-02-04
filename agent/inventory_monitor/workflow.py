"""LangGraph workflow for Inventory Monitor Agent."""

import logging
from langgraph.graph import StateGraph, END
from agent.inventory_monitor.models import InventoryState
from agent.inventory_monitor import nodes

logger = logging.getLogger(__name__)


def create_inventory_workflow(mcp_server):
    """
    Create the Inventory Monitor workflow graph.

    Args:
        mcp_server: Filesystem MCP server instance

    Returns:
        Compiled LangGraph workflow
    """
    # Create workflow graph
    workflow = StateGraph(InventoryState)

    # Define nodes
    workflow.add_node(
        "load_data",
        lambda state: nodes.load_inventory_data(state, mcp_server)
    )
    workflow.add_node("check_stock", nodes.check_stock_levels)
    workflow.add_node("generate_recommendations", nodes.generate_recommendations)

    # Define edges (workflow flow)
    workflow.set_entry_point("load_data")
    workflow.add_edge("load_data", "check_stock")
    workflow.add_edge("check_stock", "generate_recommendations")
    workflow.add_edge("generate_recommendations", END)

    # Compile the workflow
    compiled_workflow = workflow.compile()

    logger.info("Inventory Monitor workflow created successfully")

    return compiled_workflow
