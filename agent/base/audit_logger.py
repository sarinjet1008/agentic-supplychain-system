"""
Audit logging system for the Intelligent PO Assistant.

Provides session-based log files with timestamps for all agent actions.
Each new session creates a new log file in data/logs/ directory.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class AuditLogger:
    """
    Session-based audit logger that writes all agent actions to log files.

    Each session creates a new log file with format:
    data/logs/session_YYYYMMDD_HHMMSS.log
    """

    _instance: Optional['AuditLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern to ensure one audit logger per session."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the audit logger (only runs once due to singleton)."""
        if AuditLogger._initialized:
            return

        self.session_id: str = ""
        self.log_file_path: Optional[Path] = None
        self.file_handler: Optional[logging.FileHandler] = None
        self.logger: Optional[logging.Logger] = None
        AuditLogger._initialized = True

    def initialize_session(self, log_dir: str = "data/logs") -> str:
        """
        Initialize a new logging session with a unique log file.

        Args:
            log_dir: Directory to store log files

        Returns:
            Session ID (timestamp string)
        """
        # Create session ID from current timestamp
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure log directory exists
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Create log file path
        self.log_file_path = log_path / f"session_{self.session_id}.log"

        # Create dedicated audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.DEBUG)

        # Remove any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create file handler for this session
        self.file_handler = logging.FileHandler(
            self.log_file_path,
            mode='w',
            encoding='utf-8'
        )
        self.file_handler.setLevel(logging.DEBUG)

        # Create detailed formatter for audit logs
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.file_handler.setFormatter(formatter)

        # Add handler to audit logger
        self.logger.addHandler(self.file_handler)

        # Write session header
        self._write_session_header()

        return self.session_id

    def _write_session_header(self):
        """Write session header information to log file."""
        if self.logger:
            self.logger.info("=" * 80)
            self.logger.info("INTELLIGENT PO ASSISTANT - AUDIT LOG")
            self.logger.info(f"Session ID: {self.session_id}")
            self.logger.info(f"Started: {datetime.now().isoformat()}")
            self.logger.info("=" * 80)
            self.logger.info("")

    def log_action(
        self,
        agent: str,
        action: str,
        details: str = "",
        level: str = "INFO"
    ):
        """
        Log an agent action to the audit log.

        Args:
            agent: Name of the agent performing the action
            action: Description of the action being taken
            details: Additional details about the action
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        if not self.logger:
            return

        # Format the message
        message = f"[{agent}] {action}"
        if details:
            message += f" | {details}"

        # Get the appropriate log method
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)

    def log_user_input(self, message: str):
        """Log user input."""
        self.log_action("USER", "Input received", f"Message: '{message}'")

    def log_agent_response(self, agent: str, response: str):
        """Log agent response (truncated for readability)."""
        truncated = response[:200] + "..." if len(response) > 200 else response
        # Replace newlines for single-line logging
        truncated = truncated.replace('\n', ' | ')
        self.log_action(agent, "Response generated", f"Response: {truncated}")

    def log_workflow_transition(self, from_stage: str, to_stage: str, trigger: str = ""):
        """Log workflow stage transition."""
        details = f"'{from_stage}' -> '{to_stage}'"
        if trigger:
            details += f" (triggered by: {trigger})"
        self.log_action("WORKFLOW", "Stage transition", details)

    def log_mcp_call(self, server: str, tool: str, params: dict = None):
        """Log MCP server tool call."""
        details = f"Server: {server}, Tool: {tool}"
        if params:
            # Truncate large params
            params_str = str(params)[:100]
            details += f", Params: {params_str}"
        self.log_action("MCP", "Tool called", details)

    def log_a2a_message(self, source: str, target: str, method: str):
        """Log A2A protocol message."""
        self.log_action("A2A", f"Message routed", f"{source} -> {target}, Method: {method}")

    def log_hitl_gate(self, gate_name: str, status: str, user_choice: str = ""):
        """Log HITL gate interaction."""
        details = f"Gate: {gate_name}, Status: {status}"
        if user_choice:
            details += f", User choice: {user_choice}"
        self.log_action("HITL", "Gate triggered", details)

    def log_po_generated(self, po_number: str, supplier: str, total: float):
        """Log purchase order generation."""
        self.log_action(
            "PO_AGENT",
            "Purchase order generated",
            f"PO#: {po_number}, Supplier: {supplier}, Total: ${total:.2f}"
        )

    def log_validation(self, po_number: str, result: str, issues: int = 0):
        """Log PO validation result."""
        self.log_action(
            "VALIDATOR",
            "Validation completed",
            f"PO#: {po_number}, Result: {result}, Issues: {issues}"
        )

    def log_error(self, agent: str, error: str):
        """Log an error."""
        self.log_action(agent, "Error occurred", error, level="ERROR")

    def log_warning(self, agent: str, warning: str):
        """Log a warning."""
        self.log_action(agent, "Warning", warning, level="WARNING")

    def close_session(self):
        """Close the current session and finalize the log file."""
        if self.logger:
            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info(f"Session ended: {datetime.now().isoformat()}")
            self.logger.info("=" * 80)

            # Close file handler
            if self.file_handler:
                self.file_handler.close()
                self.logger.removeHandler(self.file_handler)

    def get_log_file_path(self) -> Optional[Path]:
        """Get the current log file path."""
        return self.log_file_path


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    return audit_logger
