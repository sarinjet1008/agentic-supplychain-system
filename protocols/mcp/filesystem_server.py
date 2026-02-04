"""Filesystem MCP Server - File operations for inventory data and PO documents.

This MCP server provides tools for reading inventory data from CSV files
and writing purchase order documents to the filesystem.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import logging
import json

from protocols.mcp.base_server import (
    BaseMCPServer,
    MCPError,
    MCPErrorCode
)

logger = logging.getLogger(__name__)


class FilesystemMCPServer(BaseMCPServer):
    """MCP Server for filesystem operations.

    Provides tools for:
    - Reading CSV inventory data
    - Writing purchase order documents
    - Listing available data files

    Inherits from BaseMCPServer for tool registration, error handling,
    and health check capabilities.
    """

    def __init__(self, data_dir: Path):
        """Initialize filesystem server.

        Args:
            data_dir: Directory containing data files
        """
        self.data_dir = Path(data_dir)
        self.output_dir = self.data_dir / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize base server
        super().__init__(
            server_id="filesystem_mcp",
            name="Filesystem MCP Server",
            version="1.1.0"
        )

        logger.info(f"Filesystem server data_dir: {self.data_dir}")

    def _register_tools(self) -> None:
        """Register filesystem tools."""
        self.register_tool(
            name="read_csv",
            handler=self._read_csv,
            description="Read a CSV file and return as list of dictionaries",
            input_schema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of CSV file to read"}
                },
                "required": ["filename"]
            },
            output_schema={
                "type": "array",
                "items": {"type": "object"}
            }
        )

        self.register_tool(
            name="write_po_document",
            handler=self._write_po_document,
            description="Write a purchase order document to the filesystem",
            input_schema={
                "type": "object",
                "properties": {
                    "po_number": {"type": "string", "description": "Purchase order number"},
                    "content": {"type": "string", "description": "PO document content"}
                },
                "required": ["po_number", "content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                }
            }
        )

        self.register_tool(
            name="list_inventory_files",
            handler=self._list_inventory_files,
            description="List all CSV files in the data directory",
            input_schema={"type": "object", "properties": {}},
            output_schema={
                "type": "array",
                "items": {"type": "string"}
            }
        )

        self.register_tool(
            name="read_json",
            handler=self._read_json,
            description="Read a JSON file and return parsed content",
            input_schema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of JSON file to read"}
                },
                "required": ["filename"]
            },
            output_schema={"type": "object"}
        )

        self.register_tool(
            name="write_json",
            handler=self._write_json,
            description="Write JSON content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of output file"},
                    "content": {"type": "object", "description": "JSON content to write"}
                },
                "required": ["filename", "content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                }
            }
        )

    def _get_description(self) -> str:
        """Get server description."""
        return "Provides file operations for reading inventory data and writing PO documents"

    def _read_csv(self, filename: str) -> List[Dict[str, Any]]:
        """Read a CSV file and return as list of dictionaries.

        Args:
            filename: Name of CSV file to read

        Returns:
            List of dictionaries representing CSV rows

        Raises:
            MCPError: If file doesn't exist or cannot be read
        """
        file_path = self.data_dir / filename

        if not file_path.exists():
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"File not found: {filename}",
                {"file_path": str(file_path)}
            )

        try:
            logger.info(f"Reading CSV file: {file_path}")
            df = pd.read_csv(file_path)
            data = df.to_dict('records')
            logger.info(f"Read {len(data)} rows from {filename}")
            return data

        except Exception as e:
            raise MCPError(
                MCPErrorCode.EXECUTION_ERROR,
                f"Failed to read CSV: {str(e)}",
                {"filename": filename, "error_type": type(e).__name__}
            )

    def _write_po_document(self, po_number: str, content: str) -> Dict[str, str]:
        """Write a purchase order document to the filesystem.

        Args:
            po_number: Purchase order number
            content: PO document content

        Returns:
            Dictionary with file path

        Raises:
            MCPError: If file cannot be written
        """
        filename = f"PO_{po_number}.txt"
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w') as f:
                f.write(content)

            logger.info(f"Wrote PO document: {file_path}")
            return {"file_path": str(file_path)}

        except Exception as e:
            raise MCPError(
                MCPErrorCode.EXECUTION_ERROR,
                f"Failed to write PO document: {str(e)}",
                {"po_number": po_number, "error_type": type(e).__name__}
            )

    def _list_inventory_files(self) -> List[str]:
        """List all CSV files in the data directory.

        Returns:
            List of CSV filenames
        """
        csv_files = [f.name for f in self.data_dir.glob("*.csv")]
        logger.info(f"Found {len(csv_files)} CSV files")
        return csv_files

    def _read_json(self, filename: str) -> Dict[str, Any]:
        """Read a JSON file and return parsed content.

        Args:
            filename: Name of JSON file to read

        Returns:
            Parsed JSON content

        Raises:
            MCPError: If file doesn't exist or cannot be parsed
        """
        file_path = self.data_dir / filename

        if not file_path.exists():
            raise MCPError(
                MCPErrorCode.RESOURCE_NOT_FOUND,
                f"File not found: {filename}",
                {"file_path": str(file_path)}
            )

        try:
            logger.info(f"Reading JSON file: {file_path}")
            with open(file_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Read JSON file: {filename}")
            return data

        except json.JSONDecodeError as e:
            raise MCPError(
                MCPErrorCode.EXECUTION_ERROR,
                f"Invalid JSON format: {str(e)}",
                {"filename": filename, "line": e.lineno}
            )
        except Exception as e:
            raise MCPError(
                MCPErrorCode.EXECUTION_ERROR,
                f"Failed to read JSON: {str(e)}",
                {"filename": filename, "error_type": type(e).__name__}
            )

    def _write_json(self, filename: str, content: Dict[str, Any]) -> Dict[str, str]:
        """Write JSON content to a file.

        Args:
            filename: Name of output file
            content: JSON content to write

        Returns:
            Dictionary with file path

        Raises:
            MCPError: If file cannot be written
        """
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=2)

            logger.info(f"Wrote JSON file: {file_path}")
            return {"file_path": str(file_path)}

        except Exception as e:
            raise MCPError(
                MCPErrorCode.EXECUTION_ERROR,
                f"Failed to write JSON: {str(e)}",
                {"filename": filename, "error_type": type(e).__name__}
            )

    # Backward-compatible convenience methods
    def read_csv(self, filename: str) -> List[Dict[str, Any]]:
        """Read CSV file (backward-compatible method)."""
        result = self.execute_tool("read_csv", filename=filename)
        if result.success:
            return result.data
        raise MCPError(
            MCPErrorCode(result.error["code"]),
            result.error["message"]
        )

    def write_po_document(self, po_number: str, content: str) -> str:
        """Write PO document (backward-compatible method)."""
        result = self.execute_tool("write_po_document", po_number=po_number, content=content)
        if result.success:
            return result.data["file_path"]
        raise MCPError(
            MCPErrorCode(result.error["code"]),
            result.error["message"]
        )

    def list_inventory_files(self) -> List[str]:
        """List inventory files (backward-compatible method)."""
        result = self.execute_tool("list_inventory_files")
        if result.success:
            return result.data
        raise MCPError(
            MCPErrorCode(result.error["code"]),
            result.error["message"]
        )
