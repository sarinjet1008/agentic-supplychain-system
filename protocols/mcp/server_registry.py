"""MCP Server Registry - Central registry for all MCP servers.

This module provides a registry for discovering, managing, and monitoring
all MCP servers in the system.
"""

import logging
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from protocols.mcp.base_server import BaseMCPServer, ServerInfo, ToolDefinition

logger = logging.getLogger(__name__)


class ServerStatus(str, Enum):
    """Status of an MCP server."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class ServerRegistration:
    """Registration information for an MCP server.

    Attributes:
        server: The MCP server instance
        registered_at: When the server was registered
        status: Current server status
        last_health_check: Last health check timestamp
        metadata: Additional metadata about the server
    """
    server: BaseMCPServer
    registered_at: datetime = field(default_factory=datetime.now)
    status: ServerStatus = ServerStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPServerRegistry:
    """Central registry for MCP servers.

    Provides server discovery, health monitoring, and tool lookup
    across all registered MCP servers.

    Attributes:
        servers: Dictionary of server_id -> ServerRegistration
    """

    _instance: Optional["MCPServerRegistry"] = None

    def __init__(self):
        """Initialize the server registry."""
        self.servers: Dict[str, ServerRegistration] = {}
        self._initialized = datetime.now()
        logger.info("MCP Server Registry initialized")

    @classmethod
    def get_instance(cls) -> "MCPServerRegistry":
        """Get the singleton registry instance.

        Returns:
            The global MCPServerRegistry instance
        """
        if cls._instance is None:
            cls._instance = MCPServerRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None

    def register(
        self,
        server: BaseMCPServer,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an MCP server.

        Args:
            server: The MCP server instance to register
            metadata: Optional metadata about the server
        """
        server_id = server.server_id

        if server_id in self.servers:
            logger.warning(f"Server {server_id} already registered, replacing")

        registration = ServerRegistration(
            server=server,
            metadata=metadata or {}
        )

        self.servers[server_id] = registration
        logger.info(f"Registered MCP server: {server_id} ({server.name})")

        # Perform initial health check
        self._check_server_health(server_id)

    def unregister(self, server_id: str) -> bool:
        """Unregister an MCP server.

        Args:
            server_id: ID of the server to unregister

        Returns:
            True if server was unregistered, False if not found
        """
        if server_id in self.servers:
            del self.servers[server_id]
            logger.info(f"Unregistered MCP server: {server_id}")
            return True
        return False

    def get_server(self, server_id: str) -> Optional[BaseMCPServer]:
        """Get a registered server by ID.

        Args:
            server_id: The server's unique identifier

        Returns:
            The MCP server instance or None if not found
        """
        registration = self.servers.get(server_id)
        return registration.server if registration else None

    def get_server_info(self, server_id: str) -> Optional[ServerInfo]:
        """Get server information by ID.

        Args:
            server_id: The server's unique identifier

        Returns:
            ServerInfo object or None if not found
        """
        server = self.get_server(server_id)
        return server.get_server_info() if server else None

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered servers.

        Returns:
            List of server summaries
        """
        result = []
        for server_id, registration in self.servers.items():
            info = registration.server.get_server_info()
            result.append({
                "server_id": server_id,
                "name": info.name,
                "version": info.version,
                "tools_count": len(info.tools),
                "tools": info.tools,
                "status": registration.status.value,
                "registered_at": registration.registered_at.isoformat(),
                "last_health_check": (
                    registration.last_health_check.isoformat()
                    if registration.last_health_check else None
                )
            })
        return result

    def find_tool(self, tool_name: str) -> Optional[tuple[BaseMCPServer, ToolDefinition]]:
        """Find a tool across all registered servers.

        Args:
            tool_name: Name of the tool to find

        Returns:
            Tuple of (server, tool_definition) or None if not found
        """
        for registration in self.servers.values():
            server = registration.server
            tool = server.get_tool(tool_name)
            if tool:
                return server, tool
        return None

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """List all tools from all registered servers.

        Returns:
            List of tool information with server context
        """
        tools = []
        for server_id, registration in self.servers.items():
            server = registration.server
            for tool in server.list_tools():
                tools.append({
                    "server_id": server_id,
                    "server_name": server.name,
                    "tool_name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "output_schema": tool.output_schema
                })
        return tools

    def execute_tool(
        self,
        tool_name: str,
        server_id: Optional[str] = None,
        **params
    ) -> Dict[str, Any]:
        """Execute a tool, optionally specifying the server.

        Args:
            tool_name: Name of the tool to execute
            server_id: Optional server ID (will search all servers if not specified)
            **params: Tool parameters

        Returns:
            Tool execution result
        """
        if server_id:
            server = self.get_server(server_id)
            if not server:
                return {
                    "success": False,
                    "error": f"Server not found: {server_id}"
                }
            result = server.execute_tool(tool_name, **params)
        else:
            # Find tool across all servers
            found = self.find_tool(tool_name)
            if not found:
                return {
                    "success": False,
                    "error": f"Tool not found: {tool_name}"
                }
            server, _ = found
            result = server.execute_tool(tool_name, **params)

        return result.model_dump()

    def health_check_all(self) -> Dict[str, Any]:
        """Perform health checks on all registered servers.

        Returns:
            Health check summary
        """
        results = {}
        healthy_count = 0
        unhealthy_count = 0

        for server_id in self.servers:
            health = self._check_server_health(server_id)
            results[server_id] = health

            if health.get("status") == "healthy":
                healthy_count += 1
            else:
                unhealthy_count += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "total_servers": len(self.servers),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "servers": results
        }

    def _check_server_health(self, server_id: str) -> Dict[str, Any]:
        """Check health of a specific server.

        Args:
            server_id: ID of the server to check

        Returns:
            Health check result
        """
        registration = self.servers.get(server_id)
        if not registration:
            return {"status": "not_found"}

        try:
            health = registration.server.health_check()
            registration.status = ServerStatus.HEALTHY
            registration.last_health_check = datetime.now()
            return health
        except Exception as e:
            logger.error(f"Health check failed for {server_id}: {e}")
            registration.status = ServerStatus.UNHEALTHY
            registration.last_health_check = datetime.now()
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all servers.

        Returns:
            Aggregated metrics
        """
        total_calls = 0
        total_errors = 0
        server_metrics = {}

        for server_id, registration in self.servers.items():
            metrics = registration.server.get_metrics()
            server_metrics[server_id] = metrics
            total_calls += metrics.get("total_calls", 0)
            total_errors += metrics.get("error_count", 0)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_servers": len(self.servers),
            "total_tools": sum(
                len(r.server.list_tools()) for r in self.servers.values()
            ),
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate_percent": (
                round(total_errors / total_calls * 100, 2)
                if total_calls > 0 else 0
            ),
            "servers": server_metrics
        }


def create_default_registry() -> MCPServerRegistry:
    """Create a registry with default MCP servers.

    Returns:
        Configured MCPServerRegistry instance
    """
    from protocols.mcp.filesystem_server import FilesystemMCPServer
    from protocols.mcp.api_server import APIMCPServer
    from protocols.mcp.database_server import DatabaseMCPServer

    registry = MCPServerRegistry.get_instance()

    # Register filesystem server
    fs_server = FilesystemMCPServer()
    registry.register(fs_server, {"type": "filesystem"})

    # Register API server
    api_server = APIMCPServer()
    registry.register(api_server, {"type": "api"})

    # Register database server
    db_server = DatabaseMCPServer()
    registry.register(db_server, {"type": "database"})

    logger.info(f"Default registry created with {len(registry.servers)} servers")

    return registry
