"""MCP (Model Context Protocol) servers for external data access.

This package provides MCP servers that allow agents to interact with
external resources like filesystems, databases, and APIs.

Available Servers:
- BaseMCPServer: Abstract base class with common functionality
- FilesystemMCPServer: File operations (CSV, JSON, PO documents)
- SupplierAPIMCPServer: Simulated supplier API integration
- DatabaseMCPServer: SQLite database operations

Registry:
- MCPServerRegistry: Central registry for server discovery and management

Common Classes:
- MCPError: Standard error class for MCP operations
- MCPErrorCode: Error code enumeration
- ToolDefinition: Tool schema definition
- ToolResult: Tool execution result
"""

from protocols.mcp.base_server import (
    BaseMCPServer,
    MCPError,
    MCPErrorCode,
    ToolDefinition,
    ToolResult,
    ServerInfo
)
from protocols.mcp.filesystem_server import FilesystemMCPServer
from protocols.mcp.api_server import (
    SupplierAPIMCPServer,
    QuoteRequest,
    QuoteResponse,
    get_api_server,
    get_supplier_quote
)
from protocols.mcp.database_server import DatabaseMCPServer
from protocols.mcp.server_registry import (
    MCPServerRegistry,
    ServerStatus,
    ServerRegistration,
    create_default_registry
)

__all__ = [
    # Base classes
    "BaseMCPServer",
    "MCPError",
    "MCPErrorCode",
    "ToolDefinition",
    "ToolResult",
    "ServerInfo",
    # Servers
    "FilesystemMCPServer",
    "SupplierAPIMCPServer",
    "DatabaseMCPServer",
    # Registry
    "MCPServerRegistry",
    "ServerStatus",
    "ServerRegistration",
    "create_default_registry",
    # API server helpers
    "QuoteRequest",
    "QuoteResponse",
    "get_api_server",
    "get_supplier_quote",
]
