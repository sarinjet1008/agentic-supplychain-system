"""Base MCP Server - Common functionality for all MCP servers.

This module provides a base class for MCP (Model Context Protocol) servers,
implementing common functionality like tool registration, error handling,
health checks, and logging.

MCP servers expose tools that agents can use to interact with external
resources like databases, APIs, and filesystems.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Type variable for tool return types
T = TypeVar('T')


class MCPErrorCode(Enum):
    """Standard error codes for MCP operations."""
    SUCCESS = 0
    INVALID_PARAMS = 1
    TOOL_NOT_FOUND = 2
    EXECUTION_ERROR = 3
    TIMEOUT = 4
    RESOURCE_NOT_FOUND = 5
    PERMISSION_DENIED = 6
    CONNECTION_ERROR = 7
    INTERNAL_ERROR = 99


class MCPError(Exception):
    """Exception raised by MCP operations.

    Attributes:
        code: Error code from MCPErrorCode
        message: Human-readable error message
        details: Optional additional error details
    """

    def __init__(
        self,
        code: MCPErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.name}] {message}")


class ToolDefinition(BaseModel):
    """Definition of an MCP tool.

    Attributes:
        name: Unique tool identifier
        description: Human-readable description
        input_schema: JSON Schema for tool inputs
        output_schema: JSON Schema for tool outputs
    """
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Input JSON Schema")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="Output JSON Schema")


class ToolResult(BaseModel):
    """Result of a tool execution.

    Attributes:
        success: Whether the tool executed successfully
        data: Result data (if successful)
        error: Error information (if failed)
        execution_time_ms: Time taken to execute in milliseconds
    """
    success: bool = Field(..., description="Execution success status")
    data: Optional[Any] = Field(default=None, description="Result data")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    execution_time_ms: float = Field(default=0, description="Execution time in ms")


@dataclass
class ServerInfo:
    """Information about an MCP server.

    Attributes:
        server_id: Unique server identifier
        name: Human-readable server name
        version: Server version string
        description: Server description
        tools: List of available tool names
        started_at: Server start timestamp
    """
    server_id: str
    name: str
    version: str
    description: str
    tools: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)


class BaseMCPServer(ABC):
    """Base class for MCP servers.

    Provides common functionality for all MCP servers:
    - Tool registration and discovery
    - Standardized error handling
    - Health checks
    - Execution logging and metrics

    Subclasses must implement:
    - _register_tools(): Register server-specific tools
    - get_server_info(): Return ServerInfo object
    """

    def __init__(self, server_id: str, name: str, version: str = "1.0.0"):
        """Initialize the base MCP server.

        Args:
            server_id: Unique identifier for this server
            name: Human-readable server name
            version: Server version string
        """
        self.server_id = server_id
        self.name = name
        self.version = version
        self._tools: Dict[str, Callable] = {}
        self._tool_definitions: Dict[str, ToolDefinition] = {}
        self._started_at = datetime.now()
        self._call_count = 0
        self._error_count = 0

        # Register tools from subclass
        self._register_tools()

        logger.info(
            f"MCP Server initialized: {self.name} (v{self.version}) "
            f"with {len(self._tools)} tools"
        )

    @abstractmethod
    def _register_tools(self) -> None:
        """Register server-specific tools.

        Subclasses must implement this method to register their tools
        using the register_tool() method.
        """
        pass

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a tool with the server.

        Args:
            name: Unique tool name
            handler: Function that implements the tool
            description: Human-readable description
            input_schema: Optional JSON Schema for inputs
            output_schema: Optional JSON Schema for outputs
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")

        self._tools[name] = handler
        self._tool_definitions[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema or {},
            output_schema=output_schema or {}
        )

        logger.debug(f"Registered tool: {name}")

    def execute_tool(self, tool_name: str, **params) -> ToolResult:
        """Execute a registered tool.

        Args:
            tool_name: Name of the tool to execute
            **params: Tool parameters

        Returns:
            ToolResult with execution status and data
        """
        start_time = time.time()
        self._call_count += 1

        logger.info(f"[{self.name}] Executing tool: {tool_name}")

        # Check if tool exists
        if tool_name not in self._tools:
            self._error_count += 1
            logger.error(f"Tool not found: {tool_name}")
            return ToolResult(
                success=False,
                error={
                    "code": MCPErrorCode.TOOL_NOT_FOUND.value,
                    "message": f"Tool not found: {tool_name}",
                    "available_tools": list(self._tools.keys())
                }
            )

        # Execute tool
        try:
            handler = self._tools[tool_name]
            result_data = handler(**params)

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                f"[{self.name}] Tool '{tool_name}' completed in {execution_time:.2f}ms"
            )

            return ToolResult(
                success=True,
                data=result_data,
                execution_time_ms=execution_time
            )

        except MCPError as e:
            self._error_count += 1
            execution_time = (time.time() - start_time) * 1000

            logger.error(f"[{self.name}] Tool '{tool_name}' failed: {e}")

            return ToolResult(
                success=False,
                error={
                    "code": e.code.value,
                    "message": e.message,
                    "details": e.details
                },
                execution_time_ms=execution_time
            )

        except Exception as e:
            self._error_count += 1
            execution_time = (time.time() - start_time) * 1000

            logger.error(f"[{self.name}] Tool '{tool_name}' raised exception: {e}", exc_info=True)

            return ToolResult(
                success=False,
                error={
                    "code": MCPErrorCode.EXECUTION_ERROR.value,
                    "message": str(e),
                    "error_type": type(e).__name__
                },
                execution_time_ms=execution_time
            )

    def list_tools(self) -> List[ToolDefinition]:
        """List all available tools.

        Returns:
            List of ToolDefinition objects
        """
        return list(self._tool_definitions.values())

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get definition for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolDefinition or None if not found
        """
        return self._tool_definitions.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool exists
        """
        return tool_name in self._tools

    def get_server_info(self) -> ServerInfo:
        """Get server information.

        Returns:
            ServerInfo object with server metadata
        """
        return ServerInfo(
            server_id=self.server_id,
            name=self.name,
            version=self.version,
            description=self._get_description(),
            tools=list(self._tools.keys()),
            started_at=self._started_at
        )

    def _get_description(self) -> str:
        """Get server description. Can be overridden by subclasses."""
        return f"{self.name} MCP Server"

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the server.

        Returns:
            Dictionary with health status information
        """
        uptime_seconds = (datetime.now() - self._started_at).total_seconds()
        error_rate = (self._error_count / self._call_count * 100) if self._call_count > 0 else 0

        return {
            "status": "healthy",
            "server_id": self.server_id,
            "name": self.name,
            "version": self.version,
            "uptime_seconds": uptime_seconds,
            "tools_registered": len(self._tools),
            "total_calls": self._call_count,
            "error_count": self._error_count,
            "error_rate_percent": round(error_rate, 2),
            "timestamp": datetime.now().isoformat()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics.

        Returns:
            Dictionary with server metrics
        """
        return {
            "server_id": self.server_id,
            "total_calls": self._call_count,
            "error_count": self._error_count,
            "tools": {
                name: {"description": defn.description}
                for name, defn in self._tool_definitions.items()
            }
        }
