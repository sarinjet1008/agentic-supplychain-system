"""
Main entry point for the Intelligent PO Assistant MVP.

This MVP demonstrates:
- LangGraph multi-agent workflow
- MCP (Model Context Protocol) for data access
- CLI chat interface
- Inventory monitoring
- Supplier selection
- Purchase order generation

Usage:
    python main.py
"""

import sys
import atexit
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from agent.base.shared_utils import setup_logging, load_config
from agent.base.audit_logger import get_audit_logger
from protocols.mcp.filesystem_server import FilesystemMCPServer
from agent.inventory_monitor.workflow import create_inventory_workflow
from agent.supplier_selector.workflow import create_supplier_workflow
from agent.purchase_order.workflow import create_po_workflow
from agent.orchestrator.workflow import create_orchestrator_workflow
from ui.chat_interface import ChatInterface


def main():
    """Main function to start the PO Assistant."""
    # Setup console logging
    logger = setup_logging(level=20)  # INFO level
    logger.info("Starting Intelligent PO Assistant MVP...")

    # Initialize audit logging session
    audit = get_audit_logger()
    session_id = audit.initialize_session()
    logger.info(f"Audit logging initialized - Session: {session_id}")
    logger.info(f"Audit log file: {audit.get_log_file_path()}")

    # Register cleanup handler
    atexit.register(audit.close_session)

    # Log application startup
    audit.log_action("SYSTEM", "Application started", f"Session ID: {session_id}")

    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")
        audit.log_action("SYSTEM", "Configuration loaded")

        # Initialize MCP Filesystem Server
        mcp_server = FilesystemMCPServer(data_dir=config["data_dir"])
        logger.info("MCP Filesystem Server initialized")
        audit.log_action("MCP", "Filesystem server initialized", f"Data dir: {config['data_dir']}")

        # Create Inventory Monitor workflow
        inventory_workflow = create_inventory_workflow(mcp_server)
        logger.info("Inventory Monitor workflow created")
        audit.log_action("INVENTORY_AGENT", "Workflow created")

        # Create Supplier Selector workflow
        supplier_workflow = create_supplier_workflow()
        logger.info("Supplier Selector workflow created")
        audit.log_action("SUPPLIER_AGENT", "Workflow created")

        # Create Purchase Order workflow
        po_workflow = create_po_workflow()
        logger.info("Purchase Order workflow created")
        audit.log_action("PO_AGENT", "Workflow created")

        # Create Orchestrator workflow (coordinates all three agents)
        orchestrator_workflow = create_orchestrator_workflow(
            inventory_workflow,
            supplier_workflow,
            po_workflow
        )
        logger.info("Orchestrator workflow created")
        audit.log_action("ORCHESTRATOR", "Workflow created", "All agents registered")

        # Create and run chat interface
        chat = ChatInterface(orchestrator_workflow, audit_logger=audit)
        logger.info("Chat interface initialized. Starting chat loop...")
        audit.log_action("SYSTEM", "Chat interface initialized", "Ready for user input")

        # Run the chat interface
        chat.run()

        logger.info("Application exited normally")
        audit.log_action("SYSTEM", "Application exited normally")

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease:")
        print("1. Copy .env.example to .env")
        print("2. Add your ANTHROPIC_API_KEY to the .env file")
        print("3. Run the application again")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
