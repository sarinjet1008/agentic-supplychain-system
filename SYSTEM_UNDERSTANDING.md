# System Understanding Document
## Multi-Phase Agentic AI Learning Project

**Phase 1:** Intelligent Purchase Order Assistant (Business Application)
**Phase 2:** SDLC Orchestrator with VS Code Integration (Meta Application)

**Version:** 1.1
**Date:** 2026-02-02
**Status:** ✅ Phase 1 Implementation Complete (Session 9) - Phase 2 Conceptual

---

## 1. Executive Summary

This document describes a **two-phase learning journey** for mastering modern agentic AI architectures:

**Phase 1 (Current Project):** Build an intelligent purchase order automation system that demonstrates LangGraph multi-agent framework, Deep Agents SDK, A2A protocol, MCP, and HITL patterns. Users interact via a chat interface to monitor inventory and automatically generate purchase orders when stock runs low, with human-in-the-loop approval gates at critical decision points.

**Phase 2 (Future Project):** Design and build a LangGraph-based SDLC orchestrator that manages software development lifecycle activities while seamlessly integrating with VS Code native extensions for code implementation. This demonstrates hybrid agentic architectures where LangGraph handles high-level orchestration and delegates code writing to optimized IDE tools.

**Core Value:**
- Phase 1: Learn LangGraph, Deep Agents SDK, A2A protocol, MCP, HITL through a focused business application
- Phase 2: Learn hybrid agentic architectures that combine LangGraph orchestration with native IDE tooling for optimal developer experience

---

## 2. Application Scope

### What It Does ✅
- Monitor inventory levels from CSV/database
- Detect when items fall below reorder points
- Query multiple suppliers for pricing and lead times
- Compare suppliers and recommend best option
- Generate purchase order documents
- Request human approval at key decision points
- Maintain conversation history with the user

### What It Doesn't Do ❌
- Full supply chain orchestration
- Real-time logistics tracking
- Complex demand forecasting
- Integration with real ERP systems
- Multi-warehouse management
- Advanced analytics or dashboards

---

## 3. User Interaction Model

### Chat Interface (Primary Interaction)

Users interact through a **conversational CLI chat interface** using natural language:

```
=== Intelligent PO Assistant ===
Agent: Hello! I'm your Purchase Order Assistant. I can help you monitor inventory
       and create purchase orders. What would you like to do?

User: Check my inventory status

Agent: Let me check your current inventory levels...
       [Inventory Agent working...]

       Found 2 items that need attention:
       • Laptop (Item #101): 5 units in stock (reorder point: 10)
       • Keyboard (Item #103): 8 units in stock (reorder point: 15)

       Would you like me to create purchase orders for these items?

User: Yes, create orders

Agent: I'll find the best suppliers for both items...
       [Supplier Agent working...]

       📊 Supplier Analysis Complete - Found best prices for 2 items

       🛒 Product 1 of 2:
          📦 Laptop (#101)
          📊 Quantity: 5 units
          🏪 Supplier: Global Electronics Supply
          💰 Price: $820.00/unit
          💵 Total: $4,100.00
          🚚 Delivery: 7 days
          ℹ️  Lowest cost (saves $150.00)

       🤔 Order Laptop from Global Electronics Supply? (yes/no)

User: yes

Agent: ✅ Laptop approved!

       📋 Progress: 1 of 2 products reviewed
       ✅ Approved so far: 1

       🛒 Product 2 of 2:
          📦 Keyboard (#103)
          📊 Quantity: 7 units
          🏪 Supplier: TechWorld Distributors
          💰 Price: $45.00/unit
          💵 Total: $315.00
          🚚 Delivery: 2 days

       🤔 Order Keyboard from TechWorld Distributors? (yes/no)

User: yes

Agent: ✅ Purchase Order Generation Complete!

       📄 PO-20260202-001: Global Electronics ($4,428.00 with tax)
       📄 PO-20260202-002: TechWorld Distributors ($340.20 with tax)

       💾 Saved 2 files to: data/outputs/
```

### Interface Type: CLI-Based Chat

**Initial Implementation:** Simple command-line interface
- Uses `input()` for user messages
- Uses `print()` for agent responses
- Maintains conversation state using LangGraph memory
- Supports rich text formatting (colors, emojis for better UX)

**Future Enhancement Option:** Streamlit web-based chat UI
- Can be added later without changing agent logic
- Provides browser-based interface
- Better visualization of data tables

---

## 4. Human-in-the-Loop (HITL) Integration

### HITL Approval Gates

The system includes **5 strategic HITL checkpoints**:

| Checkpoint | Trigger | User Decision | Implementation |
|-----------|---------|---------------|----------------|
| **1. Reorder Confirmation** | Items below threshold detected | Approve/reject starting PO process | Workflow stage: `awaiting_approval` |
| **2. Per-Product Approval** | Each product-supplier combination | Approve/reject each product individually | Workflow stage: `awaiting_product_approval` - loops through each product |
| **3. High-Value Approval** | PO value > $10,000 | Explicit approval required | HITLManager triggers approval dialog |
| **4. Threshold Adjustment** | Frequent low-stock alerts | Modify reorder points | Agent suggests new thresholds, user confirms |
| **5. Exception Handling** | Supplier unavailable or data issues | Manual decision needed | Agent explains issue, requests guidance |

### HITL Technical Implementation

**Using LangGraph's Built-in HITL:**
```python
# In workflow definition
graph.add_node("create_po", create_po_node)
graph.add_edge(START, "create_po")

# Add interrupt before PO creation
graph.add_conditional_edges(
    "create_po",
    interrupt_before=True,  # Pause here for approval
    condition=lambda state: state["po_value"] > 1000
)
```

**Using Deep Agents Human Approval Pattern:**
- Agents can request approval via special tool
- System pauses execution
- User provides approval/rejection via chat
- Workflow resumes with user decision

---

## 5. Technical Capabilities Demonstrated

| Capability | Implementation in This Project |
|-----------|-------------------------------|
| **LangGraph Multi-Agent** | 3 agents (Inventory, Supplier, PO) coordinated by Orchestrator via A2A |
| **Deep Agents Planning** | Orchestrator uses `write_todos` to plan 6-step workflow |
| **Deep Agents File System** | Read `inventory.csv`, write PO JSON files via MCP |
| **Deep Agents Sub-Agents** | PO agent spawns validator sub-agent for all orders |
| **A2A Protocol** | Agents communicate via `A2ARouter` with JSON-RPC messages |
| **MCP - Database** | SQLite database server with CRUD operations |
| **MCP - API** | Supplier API simulator with price variations and delays |
| **MCP - Filesystem** | Read CSV, write JSON/PO documents |
| **Custom Tools** | Calculation, comparison, validation tools |
| **Human-in-the-Loop** | 5 approval gates (per-product approval in Gate #2) |
| **Conversation Memory** | Session persistence to disk with `ConversationStore` |
| **Audit Logging** | Session-based logs in `data/logs/` with timestamps |

---

## 6. System Architecture

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User (Chat Interface)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
                ┌──────────────────────┐
                │  Orchestrator Agent  │
                │  • Plans workflow    │
                │  • Coordinates agents│
                │  • Manages HITL      │
                └──────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ↓                 ↓                 ↓
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Inventory      │ │ Supplier       │ │ Purchase Order │
│ Monitor Agent  │ │ Selector Agent │ │ Agent          │
│                │ │                │ │                │
│ • Read stock   │ │ • Query vendors│ │ • Generate PO  │
│ • Check levels │ │ • Compare deals│ │ • Spawn        │
│ • Alert on low │ │ • Recommend    │ │   validator    │
└───────┬────────┘ └───────┬────────┘ └───────┬────────┘
        │                  │                  │
        │ (via A2A)        │ (via A2A)        │
        │                  │                  │
        ↓                  ↓                  ↓
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ MCP: Database  │ │ MCP: API Server│ │ MCP: Filesystem│
│ (SQLite)       │ │ (Suppliers)    │ │ (PO Docs)      │
└────────────────┘ └────────────────┘ └────────────────┘
```

### Data Flow

```
1. User Message ("check inventory")
   ↓
2. Orchestrator receives request → Plans tasks (Deep Agents planning tool)
   ↓
3. Inventory Agent (via A2A protocol):
   - Reads inventory.csv via MCP Filesystem
   - Identifies low-stock items
   - Returns reorder recommendations
   ↓
4. HITL Gate #1: "Create orders for these items?" (yes/no)
   - Stage: awaiting_approval
   - User approves → Stage: approved
   ↓
5. Supplier Agent (via A2A protocol):
   - Loads supplier data from suppliers.json
   - Compares pricing & lead times
   - Returns best supplier for each product
   ↓
6. HITL Gate #2: Per-Product Approval (for each product)
   - Stage: awaiting_product_approval
   - Loop: "Order {product} from {supplier}?" (yes/no)
   - Tracks: current_product_index, approved_products
   - User approves/rejects each product individually
   - All products done → Stage: supplier_approved
   ↓
7. PO Agent (via A2A protocol) - only for approved products:
   - Groups items by supplier
   - Calculates totals with tax
   - Spawns validator sub-agent for validation
   - If total > $10k → HITL Gate #3: High-value approval
   - Generates PO documents
   - Saves to data/outputs/
   ↓
8. Orchestrator responds: "PO created! Files saved."
   - Stage: complete → initial

All actions logged to: data/logs/session_YYYYMMDD_HHMMSS.log
```

---

## 7. Agent Definitions

### 7.1 Orchestrator Agent

**Role:** Main coordinator and user interface manager

**Responsibilities:**
- Receive and parse user requests from chat
- Create execution plan using Deep Agents planning tool
- Spawn specialized agents via Claude Code Tasks
- Manage HITL approval gates
- Aggregate results and respond to user
- Maintain conversation state

**Tools:**
- `write_todos` (Deep Agents planning)
- `task` (spawn sub-agents)
- `a2a_send` (communicate with agents)
- `chat_respond` (send messages to user)

**State Schema:**
```python
class OrchestratorState(TypedDict):
    user_message: str
    conversation_history: List[Dict[str, str]]

    # Workflow tracking
    workflow_stage: str  # 'initial', 'awaiting_approval', 'awaiting_product_approval', 'supplier_approved', 'complete'
    pending_action: str

    # Agent results
    reorder_recommendations: List[Dict]
    inventory_summary: str
    supplier_recommendations: List[Dict]
    supplier_summary: str
    purchase_orders: List[Dict]
    po_summary: str

    # Per-product approval tracking (HITL Gate #2)
    current_product_index: int
    approved_products: List[Dict]

    # Response
    agent_response: str
```

---

### 7.2 Inventory Monitor Agent

**Role:** Check stock levels and identify reorder needs

**Responsibilities:**
- Read inventory from CSV files
- Query inventory database via MCP
- Compare current stock vs. reorder points
- Calculate quantities needed
- Report findings via A2A to Orchestrator

**Tools:**
- `read_file` (Deep Agents file tool)
- `mcp_database_query` (via MCP server)
- `a2a_send` (report results)

**State Schema:**
```python
class InventoryState(TypedDict):
    inventory_data: List[dict]
    low_stock_items: List[dict]
    reorder_recommendations: List[dict]
```

**MCP Integration:**
- Connects to SQLite database via MCP database server
- Executes: `SELECT * FROM inventory WHERE current_stock < reorder_point`

---

### 7.3 Supplier Selector Agent

**Role:** Find and compare supplier options

**Responsibilities:**
- Receive item request from Orchestrator via A2A
- Query multiple supplier APIs via MCP
- Compare pricing, lead times, reliability scores
- Rank suppliers by cost-effectiveness
- Return top 3 options + recommendation

**Tools:**
- `mcp_api_call` (query supplier APIs)
- `compare_suppliers` (custom tool)
- `a2a_send` (return results)

**State Schema:**
```python
class SupplierState(TypedDict):
    requested_item: dict
    supplier_quotes: List[dict]
    comparison_matrix: dict
    recommendation: dict
```

**MCP Integration:**
- Connects to simulated supplier APIs via MCP API server
- Calls: `GET /api/suppliers/{item_id}/quote?quantity={qty}`

---

### 7.4 Purchase Order Agent

**Role:** Generate and validate purchase orders

**Responsibilities:**
- Create PO document with all details
- Calculate total costs and taxes
- For high-value orders (>$10k), spawn validator sub-agent
- Request HITL approval before finalizing
- Save PO to filesystem via MCP

**Tools:**
- `write_file` (Deep Agents file tool)
- `task` (spawn validator sub-agent)
- `mcp_filesystem_write` (save PO document)
- `calculate_total` (custom tool)

**State Schema:**
```python
class POState(TypedDict):
    item: dict
    supplier: dict
    quantity: int
    unit_price: float
    total_cost: float
    po_number: str
    validation_status: str
```

**Sub-Agent:**
- **PO Validator Sub-Agent**: Checks business rules, credit limits, budget constraints

---

## 8. A2A Protocol Implementation

### Agent Cards (Capability Discovery)

Each agent publishes an agent card (JSON) describing its capabilities:

**Example: Inventory Monitor Agent Card**
```json
{
  "agent_id": "inventory-monitor-v1",
  "name": "Inventory Monitor Agent",
  "description": "Monitors stock levels and identifies reorder needs",
  "capabilities": [
    {
      "action": "check_inventory",
      "input_schema": {
        "item_ids": "array<string> (optional)"
      },
      "output_schema": {
        "low_stock_items": "array<object>",
        "reorder_recommendations": "array<object>"
      }
    }
  ],
  "endpoint": "http://localhost:8001/a2a",
  "auth": "bearer_token"
}
```

### A2A Message Flow

**1. Orchestrator → Inventory Agent**
```json
{
  "jsonrpc": "2.0",
  "method": "check_inventory",
  "params": {},
  "id": "req-001"
}
```

**2. Inventory Agent → Orchestrator**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "low_stock_items": [
      {"item_id": "101", "name": "Laptop", "current": 5, "reorder_point": 10}
    ]
  },
  "id": "req-001"
}
```

---

## 9. MCP Server Implementations

### 9.1 Database MCP Server

**Purpose:** Provide access to inventory database

**Implementation:**
- SQLite database: `inventory.db`
- Tables: `inventory`, `reorder_history`
- Exposes MCP tools: `query_inventory`, `update_stock`

**Example Tool:**
```python
@server.tool()
def query_inventory(item_id: Optional[str] = None):
    """Query inventory database"""
    if item_id:
        return db.execute("SELECT * FROM inventory WHERE item_id = ?", item_id)
    return db.execute("SELECT * FROM inventory WHERE current_stock < reorder_point")
```

---

### 9.2 API MCP Server

**Purpose:** Connect to supplier APIs (simulated)

**Implementation:**
- Simulates 3 supplier APIs with random pricing
- Introduces realistic delays (0.5-2s)
- Occasionally returns errors to test error handling

**Example Tool:**
```python
@server.tool()
def get_supplier_quote(supplier_id: str, item_id: str, quantity: int):
    """Get price quote from supplier"""
    # Simulate API call
    price = random.uniform(750, 900)  # Price per unit
    lead_time = random.randint(3, 14)  # Days
    return {
        "supplier_id": supplier_id,
        "item_id": item_id,
        "quantity": quantity,
        "unit_price": price,
        "lead_time_days": lead_time,
        "available": True
    }
```

---

### 9.3 Filesystem MCP Server

**Purpose:** Read/write files for inventory data and PO documents

**Implementation:**
- Provides file access to agents
- Sandboxed to specific directories
- Logs all file operations

**Example Tool:**
```python
@server.tool()
def read_csv(file_path: str):
    """Read CSV file"""
    return pd.read_csv(file_path).to_dict('records')

@server.tool()
def write_po_document(po_number: str, content: str):
    """Write purchase order document"""
    path = f"data/outputs/PO_{po_number}.txt"
    with open(path, 'w') as f:
        f.write(content)
    return {"saved": True, "path": path}
```

---

## 9.4 Audit Logging System

**Purpose:** Provide comprehensive audit trail for all agent actions

**Implementation:**
- Session-based log files in `data/logs/`
- Each new application session creates a new log file
- Filename format: `session_YYYYMMDD_HHMMSS.log`
- Singleton `AuditLogger` class ensures consistent logging

**Log Entry Format:**
```
YYYY-MM-DD HH:MM:SS | LEVEL    | AGENT_NAME               | Action | Details
```

**Logged Events:**
- `SYSTEM` - Application startup/shutdown
- `USER` - User input received
- `ORCHESTRATOR` - State transitions, workflow invocations
- `INVENTORY_AGENT` - Inventory check results
- `SUPPLIER_AGENT` - Supplier recommendations
- `PO_AGENT` - Purchase order generation
- `A2A` - Agent-to-agent message routing
- `HITL` - Human-in-the-loop gate interactions
- `MCP` - MCP server tool calls

**Example Log Output:**
```
2026-02-02 11:20:18 | INFO     | SYSTEM                    | Application started | Session ID: 20260202_112018
2026-02-02 11:20:25 | INFO     | USER                      | Input received | Message: 'check inventory'
2026-02-02 11:20:26 | INFO     | A2A                       | Message routed | orchestrator -> inventory_monitor, Method: check_inventory
2026-02-02 11:20:27 | INFO     | INVENTORY_AGENT           | Check completed | Low stock items: 2
2026-02-02 11:20:30 | INFO     | WORKFLOW                  | Stage transition | 'initial' -> 'awaiting_approval' (triggered by: check inventory)
2026-02-02 11:20:35 | INFO     | HITL                      | Gate triggered | Gate: PRODUCT_APPROVAL, Status: APPROVED, User choice: Product: Laptop
2026-02-02 11:20:40 | INFO     | PO_AGENT                  | Purchase order generated | PO#: PO-20260202-001, Supplier: Global Electronics, Total: $4428.00
```

**Usage in Code:**
```python
from agent.base.audit_logger import get_audit_logger

audit = get_audit_logger()
audit.log_action("AGENT_NAME", "Action description", "Optional details")
audit.log_user_input("user message")
audit.log_workflow_transition("old_stage", "new_stage", "trigger")
audit.log_hitl_gate("GATE_NAME", "status", "user_choice")
audit.log_po_generated("PO-001", "Supplier Name", 1000.00)
```

---

## 10. Deep Agents SDK Integration

### Planning Tool

**Usage:** Orchestrator breaks down complex requests into steps

```python
from deepagents import create_deep_agent

orchestrator = create_deep_agent(
    model="claude-3-5-sonnet",
    tools=[write_todos, task, a2a_send],
    system_prompt="You are an orchestrator agent..."
)

# Agent automatically uses write_todos when planning:
# 1. Check inventory levels
# 2. Identify items below reorder point
# 3. Query suppliers for each item
# 4. Compare supplier offers
# 5. Request user approval
# 6. Create purchase orders
```

### File System Tools

**Available to all agents:**
- `ls` - List files
- `read_file` - Read file contents
- `write_file` - Write new file
- `edit_file` - Edit existing file
- `glob` - Pattern-based file search
- `grep` - Search file contents

### Sub-Agent Tool

**PO Agent spawning validator:**
```python
if po_value > 10000:
    validation_result = task(
        agent_type="validator",
        prompt=f"Validate this high-value PO: {po_details}",
        context={"po": po_dict}
    )
```

---

## 11. Folder Structure

```
SupplyChain/
├── agent/
│   ├── base/
│   │   ├── __init__.py
│   │   ├── shared_utils.py              # Logging, config, error handling
│   │   ├── common_nodes.py              # Reusable nodes
│   │   ├── state_base.py                # Base state classes
│   │   ├── deep_agent_config.py         # Deep Agents configuration
│   │   ├── hitl_manager.py              # HITL gate management (5 gates)
│   │   ├── conversation_store.py        # Session persistence
│   │   └── audit_logger.py              # Session-based audit logging ✅ NEW
│   │
│   ├── orchestrator/
│   │   ├── models/
│   │   │   └── models.py                # OrchestratorState
│   │   ├── node/
│   │   │   ├── parse_user_input.py      # Parse chat messages
│   │   │   ├── planning_node.py         # Create execution plan
│   │   │   ├── agent_coordinator.py     # Spawn and coordinate agents
│   │   │   ├── hitl_handler.py          # Manage approval gates
│   │   │   └── response_generator.py    # Format chat responses
│   │   └── workflow/
│   │       └── orchestrator_workflow.py # Main graph
│   │
│   ├── inventory_monitor/
│   │   ├── models/
│   │   │   └── models.py                # InventoryState
│   │   ├── node/
│   │   │   ├── data_loader.py           # Load inventory data
│   │   │   ├── stock_checker.py         # Check stock levels
│   │   │   └── reorder_calculator.py    # Calculate reorder quantities
│   │   └── workflow/
│   │       └── inventory_workflow.py
│   │
│   ├── supplier_selector/
│   │   ├── models/
│   │   │   └── models.py                # SupplierState
│   │   ├── node/
│   │   │   ├── supplier_query.py        # Query supplier APIs
│   │   │   ├── price_comparator.py      # Compare quotes
│   │   │   └── recommendation.py        # Generate recommendation
│   │   └── workflow/
│   │       └── supplier_workflow.py
│   │
│   └── purchase_order/
│       ├── models/
│       │   └── models.py                # POState
│       ├── node/
│       │   ├── po_generator.py          # Create PO document
│       │   ├── cost_calculator.py       # Calculate totals
│       │   ├── validator_spawner.py     # Spawn validator sub-agent
│       │   └── po_saver.py              # Save to filesystem
│       └── workflow/
│           └── po_workflow.py
│
├── protocols/
│   ├── a2a/
│   │   ├── __init__.py
│   │   ├── client.py                    # A2A client
│   │   ├── server.py                    # A2A server
│   │   ├── agent_cards.py               # Agent card definitions
│   │   ├── message_schemas.py           # Message formats
│   │   └── adapters/
│   │       ├── orchestrator_adapter.py
│   │       ├── inventory_adapter.py
│   │       ├── supplier_adapter.py
│   │       └── po_adapter.py
│   │
│   └── mcp/
│       ├── __init__.py
│       ├── base_server.py               # Base MCP server
│       ├── database_server.py           # SQLite connector
│       ├── api_server.py                # Supplier API simulator
│       ├── filesystem_server.py         # File operations
│       └── server_registry.py           # MCP server registry
│
├── tools/
│   ├── deep_tools/
│   │   ├── __init__.py
│   │   ├── planning_tool.py             # write_todos
│   │   ├── file_tools.py                # File operations
│   │   └── subagent_tool.py             # Spawn sub-agents
│   │
│   └── custom_tools/
│       ├── __init__.py
│       ├── calculation_tools.py         # Cost calculations
│       ├── comparison_tools.py          # Supplier comparison
│       └── validation_tools.py          # Business rule validation
│
├── ui/
│   ├── __init__.py
│   └── chat_interface.py                # CLI chat interface
│
├── models/                               # Shared domain models
│   ├── __init__.py
│   ├── inventory.py
│   ├── supplier.py
│   └── purchase_order.py
│
├── config/
│   ├── agent_cards/
│   │   ├── orchestrator_card.json
│   │   ├── inventory_card.json
│   │   ├── supplier_card.json
│   │   └── po_card.json
│   ├── mcp_servers.json
│   ├── deep_agents_config.yaml
│   └── llm_config.yaml
│
├── data/
│   ├── inventory.csv                    # Sample inventory data
│   ├── inventory.db                     # SQLite database
│   ├── suppliers.json                   # Supplier directory
│   ├── outputs/                         # Generated POs
│   ├── conversations/                   # Session persistence
│   └── logs/                            # Audit logs (session_YYYYMMDD_HHMMSS.log) ✅ NEW
│
├── tests/
│   ├── unit/
│   │   ├── test_agents/
│   │   ├── test_nodes/
│   │   └── test_tools/
│   ├── integration/
│   │   ├── test_a2a.py
│   │   ├── test_mcp.py
│   │   └── test_workflows.py
│   └── fixtures/
│       ├── mock_data.py
│       └── mock_servers.py
│
├── scripts/
│   ├── setup_database.py                # Initialize SQLite DB
│   ├── setup_mcp_servers.py             # Start MCP servers
│   ├── generate_sample_data.py          # Create test data
│   └── start_chat.py                    # Launch chat interface
│
├── docs/
│   ├── architecture.md
│   ├── agent_communication.md
│   ├── mcp_integration.md
│   └── user_guide.md
│
├── .env.example
├── .gitignore
├── langgraph.json
├── pyproject.toml
├── requirements.txt
├── README.md
├── SYSTEM_UNDERSTANDING.md              # This document
└── main.py                              # Application entry point
```

---

## 12. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **LLM** | Claude 3.5 Sonnet | Primary model for agents |
| **Agent Framework** | LangGraph | Graph-based agent orchestration |
| **Agent SDK** | Deep Agents SDK | Planning, file system, sub-agents |
| **Agent Protocol** | A2A (Agent2Agent) | Inter-agent communication |
| **Context Protocol** | MCP (Model Context Protocol) | Connect to external data/tools |
| **Database** | SQLite | Inventory data storage |
| **Language** | Python 3.11+ | Implementation language |
| **UI** | CLI (rich library) | Chat interface |
| **Testing** | pytest | Unit and integration tests |
| **Task Orchestration** | Claude Code Tasks | Parallel agent execution |

### Key Python Libraries

```
langgraph>=0.2.0
deepagents>=0.1.0
anthropic>=0.40.0
python-dotenv>=1.0.0
pydantic>=2.0.0
rich>=13.0.0              # CLI formatting
pandas>=2.0.0             # Data handling
aiohttp>=3.9.0            # Async HTTP for A2A
```

---

## 13. Sample User Interactions

### Scenario 1: Basic Inventory Check

```
User: Hi, can you check my inventory?

Agent: Hello! I'll check your inventory levels right now...
       [Starting Inventory Monitor Agent...]

       📊 Inventory Status:
       ✅ Mouse - 50 units (above reorder point of 20)
       ⚠️  Laptop - 5 units (below reorder point of 10)
       ⚠️  Keyboard - 8 units (below reorder point of 15)

       I found 2 items that need reordering. Would you like me to create
       purchase orders for these items?

User: Yes please

Agent: Great! I'll find the best suppliers for both items...
       [Starting Supplier Selector Agent in parallel...]

       [2/2 items analyzed]

       Ready to create purchase orders. Let me show you the details...
```

### Scenario 2: Per-Product Approval with HITL (Gate #2)

```
Agent: 📊 Supplier Analysis Complete - Found best prices for 2 items

       🛒 Product 1 of 2:
          📦 Laptop (#101)
          📊 Quantity: 5 units
          🏪 Supplier: Global Electronics Supply
          💰 Price: $820.00/unit
          💵 Total: $4,100.00
          🚚 Delivery: 7 days
          ℹ️  Lowest cost (saves $150.00)

       🤔 Order Laptop from Global Electronics Supply? (yes/no)

User: yes

Agent: ✅ Laptop approved!

       📋 Progress: 1 of 2 products reviewed
       ✅ Approved so far: 1

       🛒 Product 2 of 2:
          📦 Keyboard (#103)
          📊 Quantity: 7 units
          🏪 Supplier: TechWorld Distributors
          💰 Price: $45.00/unit
          💵 Total: $315.00
          🚚 Delivery: 2 days

       🤔 Order Keyboard from TechWorld Distributors? (yes/no)

User: no

Agent: 📋 Product selection complete.
       Approved: 1 of 2 products

       Creating purchase order for approved items only...

       ✅ Purchase Order Generation Complete!
       📄 PO-20260202-001: Global Electronics Supply
          Items: 1
          Subtotal: $4,100.00
          Tax (8%): $328.00
          Total: $4,428.00

       💾 Saved 1 file to: data/outputs/
```

### Scenario 3: High-Value Order Approval

```
Agent: ⚠️  High-Value Order Alert

       The purchase order for Laptop is $8,200.
       This exceeds the standard approval threshold ($5,000).

       [Spawning PO Validator sub-agent...]

       ✅ Validator Check Results:
       • Budget: Available ($15,000 remaining in Q1)
       • Credit: Supplier credit limit OK
       • Business Rules: All passed

       📋 PO Summary:
       • Item: Laptop (10 units)
       • Supplier: ElectroWholesale
       • Unit Price: $820
       • Total: $8,200
       • Delivery: 7 days

       Do you approve this purchase order? (yes/no)

User: yes

Agent: ✅ Purchase order approved and created!

       📄 Document: PO_20260129_101.txt
       💾 Saved to: data/outputs/

       PO Number: PO-20260129-101
       Status: Pending Supplier Confirmation

       Would you like me to continue with the Keyboard order?
```

### Scenario 4: Threshold Adjustment

```
Agent: I notice Laptop has been flagged for reorder 3 times this week.
       Current reorder point: 10 units
       Average weekly usage: 12 units

       💡 Suggestion: Would you like to increase the reorder point to 15 units
       to reduce frequent alerts?

User: yes, update it

Agent: ✅ Reorder point updated for Laptop: 10 → 15 units
       This will be applied for future monitoring.
```

---

## 14. Success Criteria

### Functional Requirements ✅ (8/8 Complete)

- [x] User can interact via chat interface using natural language
- [x] System detects items below reorder point
- [x] System queries multiple suppliers and compares offers
- [x] User can approve/reject each product individually (per-product approval)
- [x] System creates valid PO documents (only for approved products)
- [x] High-value orders trigger validator sub-agent
- [x] User can adjust reorder thresholds (HITL Gate #4)
- [x] Conversation history is maintained (with session persistence)

### Technical Requirements ✅ (10/10 Complete)

- [x] LangGraph: 3 agents with separate workflow graphs (Inventory, Supplier, PO)
- [x] Deep Agents Planning: Orchestrator uses `write_todos` for task breakdown
- [x] Deep Agents File System: Read CSV, write PO JSON files
- [x] Deep Agents Sub-Agent: PO validator spawned for validation
- [x] A2A Protocol: Agents communicate via agent cards + JSON-RPC router
- [x] MCP Database: Database server implemented (SQLite)
- [x] MCP API: Supplier API simulator implemented
- [x] MCP Filesystem: Read/write files via MCP server
- [x] Custom Tools: calculation, comparison, validation tools
- [x] HITL: 5 approval gates implemented (per-product approval in Gate #2)

### Quality Requirements ✅ (4/6 Complete)

- [ ] All agents have unit tests (deferred to Phase 1.7)
- [ ] Integration tests for A2A communication (deferred)
- [x] Integration tests for MCP connections (manual testing)
- [x] Error handling for API failures (HITL Gate #5)
- [x] Logging for all agent actions (comprehensive + audit logging)
- [x] Documentation for all components (docstrings + YAML config)

### New Feature: Audit Logging ✅

- [x] Session-based log files (`data/logs/session_YYYYMMDD_HHMMSS.log`)
- [x] New session creates new log file
- [x] Timestamps for all actions
- [x] Logs: user input, agent responses, workflow transitions
- [x] Logs: A2A messages, HITL gates, PO generation, errors

---

## 15. Project Phases

### **PHASE 1: Intelligent PO Assistant (Current Project)**

**Goal:** Build the functional business application demonstrating LangGraph multi-agent framework, Deep Agents SDK, A2A, MCP, and HITL capabilities.

**Timeline:** 16 days

#### Phase 1.1: Foundation (Days 1-2)
- Set up project structure
- Create base utilities and shared code
- Implement data models
- Create sample data (CSV, JSON, SQLite)

#### Phase 1.2: MCP Servers (Days 3-4)
- Implement database MCP server
- Implement API MCP server (simulated suppliers)
- Implement filesystem MCP server
- Test MCP connections

#### Phase 1.3: Agent Implementation (Days 5-8)
- Build Inventory Monitor agent
- Build Supplier Selector agent
- Build Purchase Order agent
- Build Orchestrator agent
- Implement individual workflows

#### Phase 1.4: A2A Protocol (Days 9-10)
- Implement A2A client/server
- Create agent cards
- Build agent adapters
- Test inter-agent communication

#### Phase 1.5: Deep Agents Integration (Days 11-12)
- Add planning tool to Orchestrator
- Add file system tools to all agents
- Implement sub-agent spawning in PO agent
- Test Deep Agents features

#### Phase 1.6: Chat Interface + HITL (Days 13-14)
- Build CLI chat interface
- Implement HITL approval gates
- Add conversation memory
- Test user interactions

#### Phase 1.7: Testing & Documentation (Days 15-16)
- Write unit tests
- Write integration tests
- Complete documentation
- Create user guide

---

### **PHASE 2: SDLC Orchestrator System (Future Project - NOT IMPLEMENTED NOW)**

**Goal:** Build a separate LangGraph-based SDLC management system that orchestrates software development lifecycle activities while seamlessly integrating with VS Code extensions for code implementation.

**Status:** 📋 Design Only - Implementation Deferred

#### Concept Overview

A **hybrid agentic architecture** that combines:
- **LangGraph Multi-Agent Framework** for SDLC orchestration
- **VS Code Native Extensions** (Claude Code, GitHub Copilot, etc.) for code writing/editing

#### The Combo Approach

```
┌─────────────────────────────────────────────────────────────┐
│            LangGraph SDLC Orchestrator System               │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐      │
│  │ Requirements│  │ Architecture │  │ Test Strategy│      │
│  │   Agent     │  │    Agent     │  │    Agent     │      │
│  └─────────────┘  └──────────────┘  └─────────────┘      │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐      │
│  │Documentation│  │ Code Review  │  │  Deployment  │      │
│  │   Agent     │  │    Agent     │  │    Agent     │      │
│  └─────────────┘  └──────────────┘  └─────────────┘      │
│                                                             │
│              ↓ (Handoff when code needed) ↓                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
         ╔════════════════════════════════════════╗
         ║     VS Code with Native Extensions     ║
         ║  • Claude Code                         ║
         ║  • GitHub Copilot                      ║
         ║  • Other AI-powered coding assistants  ║
         ╚════════════════════════════════════════╝
                              │
                              ↓ (Results back)
         ╔════════════════════════════════════════╗
         ║  LangGraph Orchestrator Resumes        ║
         ║  • Runs tests                          ║
         ║  • Generates reports                   ║
         ║  • Updates documentation               ║
         ║  • Plans next iteration                ║
         ╚════════════════════════════════════════╝
```

#### Key Agents in SDLC Orchestrator

1. **Requirements Analyst Agent**
   - Gathers and analyzes requirements from user
   - Creates user stories and acceptance criteria
   - Identifies technical constraints
   - Output: Requirements document

2. **Architecture & Design Agent**
   - Designs system architecture
   - Creates folder structure
   - Defines data models and APIs
   - Makes technology stack decisions
   - Output: Architecture design document

3. **Test Strategy Agent**
   - Plans testing approach (unit, integration, e2e)
   - Defines test cases and coverage goals
   - Sets up testing frameworks
   - Output: Test plan document

4. **Code Orchestration Agent** (Key Integration Point)
   - **Determines what code needs to be written**
   - **Hands off to VS Code extensions** for actual coding
   - Monitors progress via file system watching
   - Collects completed code back into workflow
   - **Does NOT write code itself** - delegates to IDE

5. **Code Review Agent**
   - Reviews completed code from VS Code
   - Checks against requirements and architecture
   - Identifies issues and suggests improvements
   - Output: Code review report

6. **Test Execution Agent**
   - Runs unit and integration tests
   - Analyzes test results
   - Reports failures back to Code Orchestration Agent
   - Output: Test execution report

7. **Documentation Agent**
   - Generates API documentation
   - Creates user guides
   - Maintains architecture docs
   - Output: Documentation files

8. **Deployment Agent**
   - Plans deployment strategy
   - Creates deployment scripts
   - Manages releases
   - Output: Deployment artifacts

#### VS Code Integration Mechanism

**Handoff Protocol:**

```python
# In LangGraph Code Orchestration Agent

def delegate_to_vscode(code_task):
    """
    Hands off code implementation to VS Code extensions
    """
    # 1. Create task specification file
    task_spec = {
        "task_id": "TASK-001",
        "description": "Implement user authentication",
        "files_to_modify": ["src/auth/login.py"],
        "requirements": "Add JWT-based authentication",
        "tests_to_write": ["tests/test_auth.py"],
        "acceptance_criteria": [...]
    }
    write_file("tasks/TASK-001.json", task_spec)

    # 2. Create VS Code workspace notification
    # This could trigger a VS Code extension that:
    # - Shows task details in sidebar
    # - Opens relevant files
    # - Activates Claude Code / Copilot
    # - Guides developer through implementation

    # 3. Monitor file system for changes
    watch_files(task_spec["files_to_modify"])

    # 4. Wait for completion signal
    # Developer marks task complete in VS Code
    # Or system detects tests passing + files modified

    # 5. Validate completion
    if tests_pass() and files_updated():
        collect_results()
        return "COMPLETED"
    else:
        return "NEEDS_REVISION"
```

**VS Code Extension Integration:**
- A custom VS Code extension bridges LangGraph orchestrator and IDE
- Extension reads task specifications from `tasks/` directory
- Displays tasks in VS Code sidebar
- Activates appropriate AI coding assistant (Claude Code, Copilot)
- Developer works naturally in IDE
- Signals completion back to orchestrator

#### Why This Hybrid Approach is Superior

| Aspect | LangGraph Alone | VS Code Alone | Hybrid Approach ✅ |
|--------|-----------------|---------------|-------------------|
| **SDLC Planning** | ✅ Excellent | ❌ Limited | ✅ Best of both |
| **Code Writing** | ⚠️ Possible but not optimal | ✅ Optimized | ✅ Uses best tool |
| **Developer Experience** | ⚠️ CLI-based | ✅ Native IDE | ✅ Familiar environment |
| **Multi-Agent Orchestration** | ✅ Built-in | ❌ Not available | ✅ LangGraph handles it |
| **Context Management** | ✅ Persistent across sessions | ⚠️ Limited | ✅ Both contexts preserved |
| **Testing Orchestration** | ✅ Full control | ⚠️ Manual | ✅ Automated |
| **Documentation Generation** | ✅ Automated | ⚠️ Manual | ✅ Automated |

#### Technical Capabilities Demonstrated in Phase 2

| Capability | Phase 1 (PO Assistant) | Phase 2 (SDLC Orchestrator) |
|-----------|----------------------|----------------------------|
| **LangGraph Multi-Agent** | Business workflow agents | SDLC lifecycle agents |
| **Deep Agents Planning** | PO workflow planning | Development task planning |
| **Deep Agents Sub-Agents** | PO validator | Code review sub-agents |
| **A2A Protocol** | Agent-to-agent in same app | Cross-application agent communication |
| **MCP Servers** | Database, API, files | Git, IDE, testing frameworks |
| **HITL** | PO approval gates | Developer approval for architecture/design |
| **VS Code Integration** | N/A | **NEW: Seamless IDE handoff** |

#### Phase 2 Implementation Steps (Future)

1. **Design SDLC Orchestrator Architecture**
   - Define all 8 SDLC agents
   - Design handoff protocol with VS Code
   - Create task specification schema

2. **Build VS Code Bridge Extension**
   - Custom VS Code extension to receive tasks
   - Integration with Claude Code / Copilot
   - File system monitoring
   - Completion signaling

3. **Implement SDLC Agents**
   - Requirements, Architecture, Testing agents
   - Code Orchestration agent (handoff logic)
   - Code Review, Documentation, Deployment agents

4. **Create MCP Servers for Dev Tools**
   - Git MCP server (commits, branches, PRs)
   - IDE MCP server (open files, run commands)
   - Testing framework MCP server (pytest, jest)

5. **End-to-End Testing**
   - Test full SDLC cycle: requirement → design → code → test → deploy
   - Validate VS Code handoff works smoothly
   - Ensure context preservation across handoffs

#### Example Phase 2 Workflow

```
User: "Add user authentication to the PO Assistant app"

1. Requirements Agent:
   - Analyzes request
   - Creates user stories
   - Defines acceptance criteria
   - Output: requirements.md

2. Architecture Agent:
   - Decides on JWT-based auth
   - Plans database schema changes
   - Designs API endpoints
   - Output: architecture.md

3. Test Strategy Agent:
   - Plans unit tests for auth logic
   - Plans integration tests for endpoints
   - Output: test_plan.md

4. Code Orchestration Agent:
   - Creates task specification
   - 🔄 HANDS OFF TO VS CODE
   - Writes: tasks/AUTH-001.json

   [Developer works in VS Code with Claude Code extension]
   [VS Code shows task details, opens files, provides AI assistance]
   [Developer implements auth.py, tests pass]

   - 🔄 RECEIVES COMPLETION SIGNAL
   - Validates: ✅ Tests pass, ✅ Files updated

5. Code Review Agent:
   - Reviews implemented code
   - Checks against requirements
   - Provides feedback
   - Output: code_review.md

6. Test Execution Agent:
   - Runs full test suite
   - Confirms no regressions
   - Output: test_results.md

7. Documentation Agent:
   - Generates API docs for new endpoints
   - Updates user guide
   - Output: Updated docs/

8. Deployment Agent:
   - Updates deployment configs
   - Plans rollout strategy
   - Output: deployment_plan.md

Response to User: "Authentication added successfully! JWT-based auth
implemented with full test coverage. Documentation updated."
```

#### Benefits of Phase 2

✅ **Comprehensive SDLC Management** - Not just coding, but full lifecycle
✅ **Best Tools for Each Task** - LangGraph for orchestration, VS Code for coding
✅ **Developer-Friendly** - Coders work in familiar IDE environment
✅ **Maintains Context** - LangGraph persists project context across sessions
✅ **Automated Quality** - Testing, review, documentation all orchestrated
✅ **Advanced Learning** - Demonstrates hybrid agentic architectures

#### Phase 2 Status

**Current Status:** 📋 Conceptual Design Only
**Implementation:** Deferred until Phase 1 is complete
**Purpose:** Demonstrates advanced hybrid multi-agent architectures
**Priority:** Low (Phase 1 must succeed first)

---

**Note:** Phase 2 will be designed in detail and implemented only after successful completion of Phase 1 (Intelligent PO Assistant).

---

## 16. Sample Data

### inventory.csv
```csv
item_id,name,category,current_stock,reorder_point,unit_cost,supplier_ids
101,Laptop,Electronics,5,10,750.00,"SUP001,SUP002,SUP003"
102,Mouse,Electronics,50,20,15.00,"SUP001,SUP002"
103,Keyboard,Electronics,8,15,45.00,"SUP001,SUP003"
104,Monitor,Electronics,12,10,200.00,"SUP002,SUP003"
105,USB Cable,Accessories,100,50,3.00,"SUP001,SUP002,SUP003"
```

### suppliers.json
```json
{
  "suppliers": [
    {
      "id": "SUP001",
      "name": "TechSupply Co",
      "rating": 4.8,
      "avg_delivery_days": 3,
      "api_endpoint": "http://localhost:8001/supplier/techsupply"
    },
    {
      "id": "SUP002",
      "name": "ElectroWholesale",
      "rating": 4.5,
      "avg_delivery_days": 7,
      "api_endpoint": "http://localhost:8001/supplier/electro"
    },
    {
      "id": "SUP003",
      "name": "Global Tech",
      "rating": 4.2,
      "avg_delivery_days": 10,
      "api_endpoint": "http://localhost:8001/supplier/globaltech"
    }
  ]
}
```

---

## 17. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Complexity Creep** | Stick to defined scope; defer features to v2 |
| **A2A Protocol Learning Curve** | Start with simple JSON-RPC, use reference examples |
| **MCP Server Setup** | Begin with filesystem MCP, add DB/API incrementally |
| **Agent Coordination Bugs** | Extensive logging; test each agent independently first |
| **HITL Interrupts Not Working** | Use LangGraph built-in patterns; study documentation |
| **Claude Code Tasks Issues** | Start with sequential execution, add parallelism later |

---

## 18. Future Enhancements

### Phase 1 Enhancements (Out of Scope for Initial Implementation)

These are potential enhancements to the **Intelligent PO Assistant** application:

- 📧 Email notifications for PO creation
- 📊 Streamlit web dashboard
- 🔄 Auto-approval rules based on history
- 📈 Analytics and reporting
- 🔐 Multi-user support with authentication
- 🌐 Real supplier API integrations
- 💾 PostgreSQL instead of SQLite
- 📱 Mobile app interface
- 🤖 More specialized sub-agents (price negotiator, quality checker)
- 🔍 Advanced search and filtering in chat

### Phase 2: SDLC Orchestrator (Major Future Project)

**See Section 15 for complete details.**

A separate LangGraph-based system that manages software development lifecycle activities while seamlessly integrating with VS Code extensions for code implementation. This is a **complete separate application** that demonstrates hybrid agentic architectures.

**Status:** 📋 Design documented, implementation deferred

**Key Value:** Demonstrates how LangGraph can orchestrate high-level SDLC processes while delegating code writing to optimized IDE extensions

---

## 19. Questions for Clarification

Before implementation, please confirm:

1. **Chat Interface:** CLI-based with `rich` library for formatting is acceptable?
2. **LLM Provider:** Use Claude 3.5 Sonnet via Anthropic API?
3. **Parallel Execution:** Should we use Claude Code Tasks tool or LangGraph's built-in parallelism?
4. **Data Storage:** SQLite is sufficient, or prefer PostgreSQL?
5. **Testing Scope:** Unit tests for all nodes + integration tests for protocols?
6. **Documentation:** Inline code comments + separate markdown docs?

---

## 20. Approval Checklist

Please review and approve:

- [ ] Application scope is appropriate (not too complex, not too simple)
- [ ] Chat interface approach is suitable
- [ ] HITL integration points are sufficient
- [ ] All technical capabilities are adequately demonstrated
- [ ] Agent architecture makes sense
- [ ] Data flow is clear
- [ ] Folder structure follows best practices
- [ ] Sample interactions reflect expected behavior
- [ ] Success criteria are well-defined
- [ ] Implementation phases are realistic

---

## Next Steps

### Immediate (Phase 1 - Current Focus)

Once Phase 1 design is approved:
1. Set up project structure and dependencies
2. Create sample data files
3. Implement MCP servers
4. Build agents incrementally (Inventory, Supplier, PO, Orchestrator)
5. Integrate A2A protocol
6. Add chat interface with HITL
7. Test and refine

**Timeline:** 16 days (see Phase 1.1 - 1.7 in Section 15)

### Future (Phase 2 - After Phase 1 Success)

Once Phase 1 is complete and successful:
1. Finalize Phase 2 detailed design
2. Build VS Code bridge extension
3. Implement SDLC orchestrator agents
4. Create MCP servers for dev tools (Git, IDE, testing)
5. Test hybrid handoff between LangGraph and VS Code
6. Document best practices for hybrid architectures

**Timeline:** TBD (Phase 2 is a complete separate project)

---

**Document Status:**
- ✅ **Phase 1:** Implementation Complete (Session 9) - All features working
- 📋 **Phase 2:** Conceptual Design Complete - Implementation Deferred

**Phase 1 Implementation Highlights (Sessions 1-9):**
- ✅ 3 LangGraph agents with A2A protocol communication
- ✅ MCP servers (Filesystem, API, Database)
- ✅ Deep Agents planning tool and sub-agent spawning
- ✅ 5 HITL approval gates (including per-product approval)
- ✅ CLI chat interface with Rich formatting
- ✅ Conversation persistence and session management
- ✅ Comprehensive audit logging system

**To run:** `python main.py` → Test with `check inventory` → `yes`
