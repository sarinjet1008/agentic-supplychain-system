"""A2A Adapters - Agent adapters for A2A protocol integration.

This package provides adapters that wrap agent workflows for A2A protocol
communication. Each adapter translates between A2A messages and the
agent's native interface.

Available Adapters:
- BaseAgentAdapter: Abstract base class for adapters
- InventoryAdapter: Adapter for Inventory Monitor Agent
- SupplierAdapter: Adapter for Supplier Selector Agent
- POAdapter: Adapter for Purchase Order Agent
- OrchestratorAdapter: Adapter for Orchestrator Agent
"""

from protocols.a2a.adapters.base_adapter import BaseAgentAdapter, AdapterConfig
from protocols.a2a.adapters.inventory_adapter import InventoryAdapter
from protocols.a2a.adapters.supplier_adapter import SupplierAdapter
from protocols.a2a.adapters.po_adapter import POAdapter
from protocols.a2a.adapters.orchestrator_adapter import OrchestratorAdapter

__all__ = [
    "BaseAgentAdapter",
    "AdapterConfig",
    "InventoryAdapter",
    "SupplierAdapter",
    "POAdapter",
    "OrchestratorAdapter",
]
