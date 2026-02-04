# Quick Start Guide
## Intelligent PO Assistant - Session 3 Complete

**Last Updated:** 2026-01-30
**Status:** Ready to Run ✅

---

## Prerequisites

- Python 3.11+ installed
- Anthropic API key (get from https://console.anthropic.com/)
- Terminal/Command Prompt

---

## Setup (First Time Only)

### 1. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install pydantic pandas python-dotenv rich aiohttp jsonpatch jsonpointer langchain-core langchain langchain-anthropic langgraph anthropic
```

Or install all at once (if you trust the requirements.txt file):
```bash
pip install -r requirements.txt
```

### 3. Configure Environment

**Copy the example config:**
```bash
copy .env.example .env      # Windows
cp .env.example .env        # Linux/Mac
```

**Edit .env and add your API key:**
```bash
ANTHROPIC_API_KEY=your_actual_api_key_here

# Optional: Enable API MCP server for realistic supplier quote simulation
USE_API_MCP=false
```

---

## Running the Application

### Start the Chat Interface

```bash
python main.py
```

You should see:
```
=== Intelligent PO Assistant ===
Welcome! I can help you manage inventory and create purchase orders.

Available commands:
- check inventory : Check stock levels and identify items needing reorder
- yes/no         : Approve or reject purchase order creation
- help           : Show this help message
- quit/exit      : Exit the application

You:
```

### Test the Workflow

**Step 1: Check Inventory**
```
You: check inventory
```

**Expected Output:**
```
[Deep Agents] Generating task plan using write_todos
[A2A Router] Routing message: check_inventory (ID: ...)
[A2A Router] Invoking agent: inventory_monitor
...
⚠️  Found 2 item(s) that need reordering:
🟡 Laptop (#101): 5 units in stock (reorder at 10)
🟡 Keyboard (#103): 8 units in stock (reorder at 15)

Would you like me to help you create purchase orders for these items?
```

**Step 2: Approve PO Creation**
```
You: yes
```

**Expected Output:**
```
[A2A Router] Routing message: select_supplier
[A2A Router] Invoking agent: supplier_selector
...
📊 Supplier Analysis Complete - Found best prices for 2 item(s)
...
[A2A Router] Routing message: generate_purchase_order
[Sub-Agent] Spawning PO Validator sub-agent for validation...
[Sub-Agent] Validating PO-20260130-001 ($4,428.00)...
[Validator Sub-Agent] PO PO-20260130-001 PASSED validation
⚠️  High-value order: $4,428.00 exceeds threshold ($5,000.00) - Requires manager approval

✅ Purchase Order Generation Complete!

📄 PO-20260130-001:
   Supplier: Global Electronics
   Items: 1
   Subtotal: $4,100.00
   Tax (8%): $328.00
   Total: $4,428.00

✅ All purchase orders passed validation
💾 Saved 2 file(s) to: data/outputs
```

**Step 3: Check Generated Files**
```bash
ls data/outputs/
# Should show: PO-20260130-001.json, PO-20260130-002.json
```

---

## Advanced Features

### Enable API MCP Server (Optional)

For realistic supplier quote simulation with delays and price variations:

**Edit .env:**
```bash
USE_API_MCP=true
```

**Restart the application:**
```bash
python main.py
```

**What changes:**
- Supplier queries will have realistic delays (0.3-2.0 seconds)
- Prices will vary slightly (±8-12%) from base prices
- Occasional API errors will be logged (1-5% failure rate)

---

## What You'll See in Logs

### A2A Protocol in Action
```
[A2A Router] Initializing A2A Router for agent communication
[A2A Router] Loaded agent card: inventory_monitor (Inventory Monitor Agent)
[A2A Router] Registered workflow for agent: inventory_monitor
[A2A Router] Routing message: check_inventory (ID: abc-123)
[A2A Router] Invoking agent: inventory_monitor
[A2A Router] Agent inventory_monitor completed successfully
```

### Deep Agents Planning
```
[Deep Agents] Generating task plan using write_todos
[Deep Agents] Generated 6 task steps
📋 Task Breakdown:
1. ⏳ Check inventory levels [inventory_monitor]
2. ⏳ Query suppliers for quotes [supplier_selector]
3. ⏳ Compare prices and select best supplier [supplier_selector]
4. ⏳ Generate purchase order documents [purchase_order]
5. ⏳ Validate purchase orders [purchase_order.validator]
6. ⏳ Save PO to filesystem [purchase_order]
```

### Sub-Agent Validation
```
[Sub-Agent] Spawning PO Validator sub-agent for validation...
[Sub-Agent] Validating PO-20260130-001 ($4,428.00)...
[Validator Sub-Agent] Validating PO: PO-20260130-001
[Validator Sub-Agent] PO PO-20260130-001 PASSED validation
[Sub-Agent] Validation complete: PASSED (6/6 checks)
```

### API MCP Server (if enabled)
```
[MCP API] Using API MCP Server for supplier quotes
[MCP API] Requesting quote from SUP001 for #101 (qty: 10)
[MCP API] Simulating API delay: 1.23s
[MCP API] Got quote from TechWorld: $245.50/unit (±8% variation)
[MCP API] Collected 8 quotes via API (some suppliers may have failed)
```

---

## Troubleshooting

### Issue: ModuleNotFoundError
**Solution:** Make sure virtual environment is activated and dependencies are installed:
```bash
# Activate venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install pydantic pandas python-dotenv rich aiohttp jsonpatch jsonpointer langchain-core langchain langchain-anthropic langgraph anthropic
```

### Issue: API Key Error
**Solution:** Check your .env file has the correct API key:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Issue: No low stock items found
**Solution:** Modify inventory.csv to lower stock quantities:
```csv
item_id,name,category,unit_price,quantity_on_hand,reorder_point,supplier_id
101,Laptop,Electronics,1000,2,10,SUP002
```

### Issue: Import errors for new modules
**Solution:** Make sure you're running from the project root directory:
```bash
cd c:\AgenticAI_Exp\SupplyChain
python main.py
```

---

## Project Structure

```
SupplyChain/
├── agent/                          # Agent implementations
│   ├── base/                       # Shared utilities
│   ├── orchestrator/               # Orchestrator agent
│   ├── inventory_monitor/          # Inventory monitoring
│   ├── supplier_selector/          # Supplier selection
│   └── purchase_order/             # PO generation + validator
│       └── validator.py            # PO validator sub-agent ✨
├── protocols/                      # Communication protocols
│   ├── a2a/                        # A2A protocol ✨
│   │   ├── message_schemas.py      # Request/response classes
│   │   └── router.py               # A2A router
│   └── mcp/                        # MCP servers
│       ├── filesystem_server.py    # File operations
│       └── api_server.py           # Supplier API simulation ✨
├── tools/                          # Deep Agents tools ✨
│   └── deep_tools/                 # Deep Agents SDK tools
│       ├── planning_tool.py        # write_todos
│       └── file_tools.py           # File operations
├── config/                         # Configuration
│   └── agent_cards/                # Agent capability descriptors ✨
│       ├── inventory_card.json
│       ├── supplier_card.json
│       └── purchase_order_card.json
├── data/                           # Data files
│   ├── inventory.csv               # Sample inventory
│   ├── suppliers.json              # Supplier catalog
│   └── outputs/                    # Generated POs
├── ui/                             # User interface
│   └── chat_interface.py           # CLI chat
├── models/                         # Domain models
│   └── inventory.py                # Inventory models
├── main.py                         # Application entry point
├── .env                            # Configuration (create from .env.example)
└── requirements.txt                # Python dependencies

✨ = New in Session 3
```

---

## Next Steps

### 1. Explore the Code
- Read [SESSION_3_SUMMARY.md](SESSION_3_SUMMARY.md) for detailed documentation
- Check [PROGRESS.md](PROGRESS.md) for full project history
- Review agent cards in [config/agent_cards/](config/agent_cards/)

### 2. Customize the System
- Modify inventory data in [data/inventory.csv](data/inventory.csv)
- Add suppliers in [data/suppliers.json](data/suppliers.json)
- Adjust validation rules in [agent/purchase_order/validator.py](agent/purchase_order/validator.py)

### 3. Extend the Features
- Add more HITL approval gates
- Implement email notifications
- Create PO approval workflow
- Add inventory update after PO confirmation

### 4. Testing & Documentation
- Write unit tests with pytest
- Add integration tests
- Create comprehensive API documentation
- Add error handling improvements

---

## Architecture Highlights

### 🔄 A2A Protocol
All agents communicate through a standardized JSON-RPC protocol:
```
User → Orchestrator → A2A Router → Inventory Monitor Agent
                                 → Supplier Selector Agent
                                 → Purchase Order Agent → Validator Sub-Agent
```

### 🧠 Deep Agents Planning
Task breakdown with dependencies:
```
write_todos("create purchase orders")
→ 6 steps with dependencies
→ Visible in logs
→ Enables autonomous planning
```

### 🤖 Sub-Agent Pattern
PO validator spawned as sub-agent:
```
PO Agent → Spawn Validator
         → Run 6 validation checks
         → Return results
         → Continue workflow
```

### 🌐 MCP Servers
3 MCP servers for data access:
- **Filesystem:** Read CSV, write JSON
- **API:** Simulate supplier APIs (optional)
- **Database:** Not needed (using CSV)

---

## Support

**Documentation:**
- [SESSION_3_SUMMARY.md](SESSION_3_SUMMARY.md) - Session 3 details
- [PROGRESS.md](PROGRESS.md) - Full project tracking
- [SYSTEM_UNDERSTANDING.md](SYSTEM_UNDERSTANDING.md) - Architecture guide

**Issues:**
- Check logs for errors
- Verify .env configuration
- Ensure virtual environment is activated
- Check Python version (3.11+ required)

---

**Ready to Build More?**

This project demonstrates:
- ✅ LangGraph multi-agent workflows
- ✅ A2A protocol for agent communication
- ✅ Deep Agents SDK (planning, file tools, sub-agents)
- ✅ MCP servers for external data access
- ✅ HITL approval gates
- ✅ Comprehensive logging and error handling

**Next Phase:** Testing, documentation, or Phase 2 (SDLC Orchestrator)

---

**Last Updated:** 2026-01-30
**Project Status:** Complete MVP - Ready for Production Testing ✅
