"""CLI Chat Interface for the PO Assistant.

This module provides an interactive command-line interface with:
- Rich text formatting
- HITL (Human-in-the-Loop) approval gates
- Conversation persistence
- Session management
- Audit logging
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt, Confirm

from agent.base.hitl_manager import (
    HITLManager,
    HITLRequest,
    HITLResponse,
    HITLStatus,
    HITLGateType,
    get_hitl_manager,
)
from agent.base.conversation_store import (
    ConversationStore,
    get_conversation_store,
)
from agent.base.audit_logger import AuditLogger, get_audit_logger

logger = logging.getLogger(__name__)


class ChatInterface:
    """Enhanced CLI chat interface with HITL support and persistence."""

    def __init__(self, orchestrator_workflow, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize chat interface.

        Args:
            orchestrator_workflow: Compiled orchestrator workflow
            audit_logger: Optional audit logger instance
        """
        self.orchestrator = orchestrator_workflow
        self.console = Console()
        self.hitl_manager = get_hitl_manager()
        self.conversation_store = get_conversation_store()
        self.audit = audit_logger or get_audit_logger()

        # Initialize or load session
        self._initialize_session()

    def _initialize_session(self):
        """Initialize or resume a conversation session."""
        # Try to load latest session or create new one
        existing_sessions = self.conversation_store.list_sessions()

        if existing_sessions:
            # Ask user if they want to resume
            latest = existing_sessions[0]
            message_count = latest.get("message_count", 0)

            if message_count > 0:
                self.console.print(
                    f"\n[dim]Found previous session with {message_count} messages.[/dim]"
                )
                try:
                    resume = Confirm.ask("Would you like to resume the previous session?", default=False)

                    if resume:
                        session = self.conversation_store.load_session(latest["session_id"])
                        if session:
                            self.console.print("[green]Session resumed.[/green]\n")
                            return
                except Exception:
                    # Non-interactive mode, create new session
                    pass

        # Create new session
        self.conversation_store.create_session(metadata={"source": "cli"})

    @property
    def conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history from the store."""
        return self.conversation_store.get_conversation_history()

    @property
    def workflow_state(self) -> Dict[str, Any]:
        """Get workflow state from the store."""
        state = self.conversation_store.get_workflow_state()
        if not state:
            state = {
                "workflow_stage": "initial",
                "pending_action": "none",
                "reorder_recommendations": [],
                "supplier_recommendations": [],
                "purchase_orders": [],
                "pending_hitl_request": None,
            }
            self.conversation_store.update_workflow_state(state)
        return state

    def _update_workflow_state(self, updates: Dict[str, Any]):
        """Update workflow state in the store."""
        state = self.workflow_state.copy()
        state.update(updates)
        self.conversation_store.update_workflow_state(state)

    def show_welcome(self):
        """Display welcome message."""
        welcome_text = """
# Welcome to the Intelligent PO Assistant!

I can help you monitor inventory and manage purchase orders.

**Available commands:**
- `check inventory` - Check current inventory levels
- `history` - View conversation history
- `sessions` - Manage conversation sessions
- `help` - Show this help message
- `quit` or `exit` - Exit the application

**HITL Gates:**
- Gate 1: PO Creation Approval
- Gate 2: Supplier Selection
- Gate 3: High-Value PO Approval (>$10,000)
- Gate 4: Threshold Adjustment
- Gate 5: Exception Handling

Type your message below to get started!
        """

        self.console.print(Panel(
            Markdown(welcome_text),
            title="[bold blue]PO Assistant - Phase 1.6 Complete[/bold blue]",
            border_style="blue"
        ))

    def get_user_input(self) -> str:
        """
        Get input from user.

        Returns:
            User's input message
        """
        self.console.print("\n[bold cyan]You:[/bold cyan] ", end="")
        return input().strip()

    def show_agent_response(self, message: str):
        """
        Display agent's response.

        Args:
            message: Response message to display
        """
        self.console.print(f"\n[bold green]Agent:[/bold green]\n{message}")

    def show_hitl_request(self, request: HITLRequest) -> str:
        """
        Display an HITL request and get user response.

        Args:
            request: HITLRequest to display

        Returns:
            User's response string
        """
        # Format the request
        formatted = self.hitl_manager.format_request_for_display(request)
        self.console.print(formatted)

        # Get user input
        response = self.get_user_input()
        return response

    def handle_supplier_selection(
        self,
        product_name: str,
        supplier_options: List[Dict[str, Any]],
        recommended_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Handle HITL Gate #2: Supplier Selection.

        Args:
            product_name: Name of the product
            supplier_options: List of supplier options
            recommended_id: ID of recommended supplier

        Returns:
            Selected supplier data or None if cancelled
        """
        request = self.hitl_manager.create_supplier_selection_request(
            product_name=product_name,
            supplier_options=supplier_options,
            recommended_supplier_id=recommended_id
        )

        # Display as a table
        table = Table(title=f"Supplier Options for {product_name}")
        table.add_column("#", style="cyan")
        table.add_column("Supplier", style="green")
        table.add_column("Price", style="yellow")
        table.add_column("Lead Time", style="blue")
        table.add_column("Rating", style="magenta")

        for i, supplier in enumerate(supplier_options, 1):
            is_rec = supplier.get("supplier_id") == recommended_id
            name = supplier.get("supplier_name", "Unknown")
            if is_rec:
                name += " [bold](Recommended)[/bold]"

            table.add_row(
                str(i),
                name,
                f"${supplier.get('unit_price', 0):.2f}",
                f"{supplier.get('lead_time_days', 0)} days",
                f"{supplier.get('rating', 0):.1f}/5.0"
            )

        self.console.print("\n")
        self.console.print(table)
        self.console.print("\nEnter the number of your choice (or 'skip' to use recommendation):")

        response = self.get_user_input()

        # Process response
        if response.lower() in ["skip", "s", ""]:
            # Use recommendation
            for s in supplier_options:
                if s.get("supplier_id") == recommended_id:
                    logger.info(f"[HITL Gate #2] User accepted recommendation: {recommended_id}")
                    return s
            return supplier_options[0] if supplier_options else None

        try:
            choice = int(response)
            if 1 <= choice <= len(supplier_options):
                selected = supplier_options[choice - 1]
                logger.info(f"[HITL Gate #2] User selected: {selected.get('supplier_id')}")
                return selected
        except ValueError:
            pass

        # Try matching by name or ID
        for s in supplier_options:
            if (response.lower() in s.get("supplier_name", "").lower() or
                response.upper() == s.get("supplier_id", "")):
                logger.info(f"[HITL Gate #2] User selected by name/ID: {s.get('supplier_id')}")
                return s

        logger.warning(f"[HITL Gate #2] Invalid selection, using recommendation")
        for s in supplier_options:
            if s.get("supplier_id") == recommended_id:
                return s
        return supplier_options[0] if supplier_options else None

    def handle_high_value_approval(
        self,
        po_number: str,
        total_amount: float,
        supplier_name: str,
        line_items: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle HITL Gate #3: High-Value PO Approval.

        Args:
            po_number: PO number
            total_amount: Total amount
            supplier_name: Supplier name
            line_items: List of line items

        Returns:
            Tuple of (approved, reason)
        """
        request = self.hitl_manager.create_high_value_approval_request(
            po_number=po_number,
            total_amount=total_amount,
            supplier_name=supplier_name,
            line_items=line_items
        )

        self.console.print("\n" + "="*50)
        self.console.print("[bold red]HIGH-VALUE PURCHASE ORDER[/bold red]")
        self.console.print("="*50)
        self.console.print(f"\nPO Number: {po_number}")
        self.console.print(f"Supplier: {supplier_name}")
        self.console.print(f"[bold]Total: ${total_amount:,.2f}[/bold]")
        threshold = self.hitl_manager.gate_configs[HITLGateType.HIGH_VALUE_APPROVAL]['threshold']
        self.console.print(f"\nThis exceeds the ${threshold:,.2f} threshold.")

        # Show line items
        table = Table(title="Line Items")
        table.add_column("Product")
        table.add_column("Qty")
        table.add_column("Price")
        table.add_column("Total")

        for item in line_items:
            table.add_row(
                item.get("product_name", "Unknown"),
                str(item.get("quantity", 0)),
                f"${item.get('unit_price', 0):.2f}",
                f"${item.get('line_total', 0):.2f}"
            )

        self.console.print(table)

        try:
            approved = Confirm.ask("\nDo you approve this purchase order?", default=False)

            reason = None
            if approved:
                reason = Prompt.ask("Please provide approval reason (optional)", default="")
            else:
                reason = Prompt.ask("Please provide rejection reason", default="Budget constraints")
        except Exception:
            # Non-interactive mode
            approved = False
            reason = "Non-interactive mode - auto-rejected"

        logger.info(f"[HITL Gate #3] High-value PO {po_number}: {'APPROVED' if approved else 'REJECTED'}")
        return (approved, reason if reason else None)

    def handle_threshold_adjustment(
        self,
        product_id: str,
        product_name: str,
        current_value: int,
        suggested_value: int,
        reason: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Handle HITL Gate #4: Threshold Adjustment.

        Args:
            product_id: Product identifier
            product_name: Product name
            current_value: Current reorder point
            suggested_value: Suggested new value
            reason: Reason for suggestion

        Returns:
            Tuple of (approved, new_value or None)
        """
        self.console.print("\n" + "="*50)
        self.console.print("[bold yellow]THRESHOLD ADJUSTMENT REQUEST[/bold yellow]")
        self.console.print("="*50)
        self.console.print(f"\nProduct: {product_name} ({product_id})")
        self.console.print(f"Current Reorder Point: {current_value} units")
        self.console.print(f"Suggested Reorder Point: {suggested_value} units")
        self.console.print(f"Reason: {reason}")

        self.console.print("\nOptions:")
        self.console.print("  1. Apply suggested change")
        self.console.print("  2. Keep current value")
        self.console.print("  3. Enter custom value")

        try:
            choice = Prompt.ask("Select option", choices=["1", "2", "3"], default="2")
        except Exception:
            choice = "2"

        if choice == "1":
            logger.info(f"[HITL Gate #4] Threshold adjusted to {suggested_value}")
            return (True, suggested_value)
        elif choice == "3":
            try:
                custom = Prompt.ask("Enter new reorder point", default=str(current_value))
                new_value = int(custom)
                logger.info(f"[HITL Gate #4] Threshold set to custom value {new_value}")
                return (True, new_value)
            except (ValueError, Exception):
                logger.warning("[HITL Gate #4] Invalid input, keeping current")
                return (False, None)
        else:
            logger.info("[HITL Gate #4] Keeping current threshold")
            return (False, None)

    def handle_exception(
        self,
        exception_type: str,
        exception_message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Handle HITL Gate #5: Exception Handling.

        Args:
            exception_type: Type of exception
            exception_message: Error message
            context: Context information

        Returns:
            User's chosen action (retry, skip, abort)
        """
        self.console.print("\n" + "="*50)
        self.console.print("[bold red]EXCEPTION HANDLING REQUIRED[/bold red]")
        self.console.print("="*50)
        self.console.print(f"\nType: {exception_type}")
        self.console.print(f"Message: {exception_message}")

        if context:
            self.console.print("\nContext:")
            for k, v in context.items():
                self.console.print(f"  - {k}: {v}")

        self.console.print("\nHow would you like to proceed?")
        self.console.print("  1. [bold]retry[/bold] - Retry the failed operation")
        self.console.print("  2. [bold]skip[/bold] - Skip this item and continue")
        self.console.print("  3. [bold]abort[/bold] - Abort the entire workflow")

        try:
            choice = Prompt.ask("Select action", choices=["1", "2", "3", "retry", "skip", "abort"], default="skip")
        except Exception:
            choice = "skip"

        action_map = {"1": "retry", "2": "skip", "3": "abort"}
        action = action_map.get(choice, choice)

        logger.info(f"[HITL Gate #5] User chose: {action}")
        return action

    def show_history(self):
        """Display conversation history."""
        history = self.conversation_history

        if not history:
            self.console.print("[dim]No conversation history.[/dim]")
            return

        self.console.print("\n[bold]Conversation History:[/bold]")
        self.console.print("-" * 40)

        for msg in history[-20:]:  # Show last 20 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                self.console.print(f"[cyan]You:[/cyan] {content[:100]}...")
            else:
                self.console.print(f"[green]Agent:[/green] {content[:100]}...")

        self.console.print("-" * 40)

    def manage_sessions(self):
        """Session management interface."""
        sessions = self.conversation_store.list_sessions()

        if not sessions:
            self.console.print("[dim]No saved sessions.[/dim]")
            return

        self.console.print("\n[bold]Saved Sessions:[/bold]")

        table = Table()
        table.add_column("#")
        table.add_column("Session ID")
        table.add_column("Created")
        table.add_column("Messages")

        for i, session in enumerate(sessions[:10], 1):
            table.add_row(
                str(i),
                session.get("session_id", "")[:8],
                session.get("created_at", "")[:10],
                str(session.get("message_count", 0))
            )

        self.console.print(table)

        self.console.print("\nOptions: [bold]load <#>[/bold], [bold]delete <#>[/bold], [bold]clear all[/bold], [bold]back[/bold]")

        try:
            action = Prompt.ask("Action", default="back")
        except Exception:
            return

        if action.startswith("load "):
            try:
                idx = int(action.split()[1]) - 1
                if 0 <= idx < len(sessions):
                    session = self.conversation_store.load_session(sessions[idx]["session_id"])
                    if session:
                        self.console.print("[green]Session loaded.[/green]")
            except (ValueError, IndexError):
                self.console.print("[red]Invalid selection.[/red]")

        elif action.startswith("delete "):
            try:
                idx = int(action.split()[1]) - 1
                if 0 <= idx < len(sessions):
                    if Confirm.ask("Are you sure?", default=False):
                        self.conversation_store.delete_session(sessions[idx]["session_id"])
                        self.console.print("[yellow]Session deleted.[/yellow]")
            except (ValueError, IndexError):
                self.console.print("[red]Invalid selection.[/red]")

        elif action == "clear all":
            try:
                if Confirm.ask("Delete ALL sessions?", default=False):
                    self.conversation_store.clear_all_sessions()
                    self.conversation_store.create_session()
                    self.console.print("[yellow]All sessions cleared.[/yellow]")
            except Exception:
                pass

    def handle_user_message(self, user_message: str) -> bool:
        """
        Process user message and get agent response.

        Args:
            user_message: User's input message

        Returns:
            True to continue chat, False to exit
        """
        # Log user input
        self.audit.log_user_input(user_message)

        # Check for exit commands
        if user_message.lower() in ["quit", "exit", "bye"]:
            self.conversation_store.save_session()
            self.audit.log_action("SYSTEM", "Session ended by user")
            self.console.print("\n[bold yellow]Session saved. Goodbye![/bold yellow]\n")
            return False

        # Check for help command
        if user_message.lower() in ["help", "?"]:
            self.audit.log_action("CHAT", "Help displayed")
            self.show_welcome()
            return True

        # Check for history command
        if user_message.lower() == "history":
            self.audit.log_action("CHAT", "History displayed")
            self.show_history()
            return True

        # Check for sessions command
        if user_message.lower() == "sessions":
            self.audit.log_action("CHAT", "Session management opened")
            self.manage_sessions()
            return True

        # Add user message to conversation store
        self.conversation_store.add_message("user", user_message)

        try:
            # Get current workflow state
            state = self.workflow_state.copy()
            old_stage = state.get('workflow_stage', 'initial')
            logger.info(f"[ChatInterface] Loaded state: stage={old_stage}, recs={len(state.get('reorder_recommendations', []))}")
            self.audit.log_action("ORCHESTRATOR", "State loaded", f"Stage: {old_stage}")

            # Create orchestrator state
            state.update({
                "user_message": user_message,
                "conversation_history": self.conversation_history,
                "inventory_summary": "",
                "supplier_summary": "",
                "po_summary": "",
                "agent_response": ""
            })

            # Run orchestrator workflow
            self.audit.log_action("ORCHESTRATOR", "Workflow invoked", f"Input: '{user_message[:50]}...'")
            result = self.orchestrator.invoke(state)

            # Update workflow state - serialize Pydantic objects to dicts for JSON storage
            reorder_recs = result.get("reorder_recommendations", [])
            serialized_recs = []
            for rec in reorder_recs:
                if hasattr(rec, 'model_dump'):
                    serialized_recs.append(rec.model_dump())
                elif isinstance(rec, dict):
                    serialized_recs.append(rec)
                else:
                    serialized_recs.append({})

            new_stage = result.get("workflow_stage", "initial")
            logger.info(f"[ChatInterface] Workflow result: stage={new_stage}, recs={len(serialized_recs)}")

            # Log stage transition if changed
            if old_stage != new_stage:
                self.audit.log_workflow_transition(old_stage, new_stage, user_message[:30])

            self._update_workflow_state({
                "workflow_stage": new_stage,
                "pending_action": result.get("pending_action", "none"),
                "reorder_recommendations": serialized_recs,
                "supplier_recommendations": result.get("supplier_recommendations", []),
                "purchase_orders": result.get("purchase_orders", []),
                "approved_products": result.get("approved_products", []),
                "current_product_index": result.get("current_product_index", 0)
            })

            # Get agent response
            agent_response = result.get("agent_response", "Sorry, I couldn't process that request.")

            # Check for high-value POs requiring approval (Gate #3)
            pos = result.get("purchase_orders", [])
            for po in pos:
                total = po.get("total_amount", 0)
                if self.hitl_manager.check_high_value_threshold(total):
                    self.audit.log_hitl_gate("HIGH_VALUE_APPROVAL", "triggered", f"PO: {po.get('po_number')}, Total: ${total:.2f}")
                    approved, reason = self.handle_high_value_approval(
                        po_number=po.get("po_number", ""),
                        total_amount=total,
                        supplier_name=po.get("supplier_name", ""),
                        line_items=po.get("line_items", [])
                    )
                    self.audit.log_hitl_gate("HIGH_VALUE_APPROVAL", "APPROVED" if approved else "REJECTED", reason or "")
                    if not approved:
                        agent_response += f"\n\n[PO {po.get('po_number')} was rejected: {reason}]"

            # Show response
            self.show_agent_response(agent_response)
            self.audit.log_agent_response("ORCHESTRATOR", agent_response)

            # Add to conversation store
            self.conversation_store.add_message("assistant", agent_response)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            self.audit.log_error("ORCHESTRATOR", str(e))
            self.console.print(f"\n[bold red]Error:[/bold red] {str(e)}")

            # Offer exception handling (Gate #5)
            self.audit.log_hitl_gate("EXCEPTION_HANDLING", "triggered", str(e)[:100])
            action = self.handle_exception(
                exception_type=type(e).__name__,
                exception_message=str(e),
                context={"user_message": user_message}
            )
            self.audit.log_hitl_gate("EXCEPTION_HANDLING", "resolved", f"Action: {action}")

            if action == "abort":
                return False

        return True

    def run(self):
        """Run the chat interface loop."""
        self.show_welcome()

        while True:
            try:
                user_message = self.get_user_input()

                if not user_message:
                    continue

                # Process message
                should_continue = self.handle_user_message(user_message)

                if not should_continue:
                    break

            except KeyboardInterrupt:
                self.conversation_store.save_session()
                self.console.print("\n\n[bold yellow]Session saved. Interrupted. Goodbye![/bold yellow]\n")
                break
            except EOFError:
                self.conversation_store.save_session()
                self.console.print("\n[bold yellow]Session saved. Goodbye![/bold yellow]\n")
                break
