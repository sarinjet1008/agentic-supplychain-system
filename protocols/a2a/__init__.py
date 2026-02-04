"""Agent-to-Agent (A2A) Protocol Implementation.

This module provides the infrastructure for agents to communicate with each other
using a standardized JSON-RPC style protocol.

Components:
- Message Schemas: A2ARequest, A2AResponse for message format
- Router: Routes messages to appropriate agents
- Client: Sends requests to other agents
- Server: Receives and handles requests
- Agent Cards: Capability definitions for discovery
- Adapters: Wrappers for integrating agent workflows
"""

from protocols.a2a.message_schemas import (
    A2ARequest,
    A2AResponse,
    A2AError,
    create_request,
    create_response,
    create_error_response,
)
from protocols.a2a.router import A2ARouter
from protocols.a2a.client import A2AClient, A2AClientPool, A2AClientError
from protocols.a2a.server import A2AServer, RequestHandler, HandlerStatus, create_agent_server
from protocols.a2a.agent_cards import (
    AgentCard,
    AgentCapability,
    AgentCardRegistry,
    create_agent_card,
    get_default_registry,
    INVENTORY_MONITOR_CARD,
    SUPPLIER_SELECTOR_CARD,
    PURCHASE_ORDER_CARD,
    ORCHESTRATOR_CARD,
)
from protocols.a2a.adapters import (
    BaseAgentAdapter,
    AdapterConfig,
    InventoryAdapter,
    SupplierAdapter,
    POAdapter,
    OrchestratorAdapter,
)

__all__ = [
    # Message schemas
    "A2ARequest",
    "A2AResponse",
    "A2AError",
    "create_request",
    "create_response",
    "create_error_response",
    # Router
    "A2ARouter",
    # Client
    "A2AClient",
    "A2AClientPool",
    "A2AClientError",
    # Server
    "A2AServer",
    "RequestHandler",
    "HandlerStatus",
    "create_agent_server",
    # Agent cards
    "AgentCard",
    "AgentCapability",
    "AgentCardRegistry",
    "create_agent_card",
    "get_default_registry",
    "INVENTORY_MONITOR_CARD",
    "SUPPLIER_SELECTOR_CARD",
    "PURCHASE_ORDER_CARD",
    "ORCHESTRATOR_CARD",
    # Adapters
    "BaseAgentAdapter",
    "AdapterConfig",
    "InventoryAdapter",
    "SupplierAdapter",
    "POAdapter",
    "OrchestratorAdapter",
]
