# Intelligent PO Assistant - MVP

A multi-agent system for intelligent purchase order automation built with LangGraph.

## 🎯 What This MVP Does

- ✅ Monitor inventory levels from CSV data
- ✅ Detect items below reorder point
- ✅ Generate reorder recommendations
- ✅ Chat interface for user interaction
- ✅ LangGraph multi-agent workflow
- ✅ MCP (Model Context Protocol) for data access

## 📋 Prerequisites

- Python 3.11 or higher
- Anthropic API key (for Claude)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Run the Application

```bash
python main.py
```

## 💬 Using the Chat Interface

Once started, you can use these commands:

- `check inventory` - Check current inventory levels and get reorder recommendations
- `help` - Show available commands
- `quit` or `exit` - Exit the application

### Example Session

```
You: check inventory

Agent:
⚠️  Found 2 item(s) that need reordering:

🔴 Laptop (#101): 5 units in stock (reorder at 10)
🟡 Keyboard (#103): 8 units in stock (reorder at 15)

Would you like me to help you create purchase orders for these items?
```

## 📁 Project Structure

```
SupplyChain/
├── agent/                      # Agent implementations
│   ├── base/                  # Shared utilities
│   ├── inventory_monitor/     # Inventory monitoring agent
│   └── orchestrator/          # Orchestrator agent
├── protocols/                  # Protocol implementations
│   └── mcp/                   # MCP servers
├── models/                     # Domain models
├── ui/                         # User interface
├── data/                       # Data files
│   ├── inventory.csv          # Sample inventory data
│   └── outputs/               # Generated PO documents
└── main.py                     # Application entry point
```

## 🔧 Configuration

Edit `.env` to configure:

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `MODEL` - Claude model to use (default: claude-3-5-sonnet-20241022)
- `TEMPERATURE` - Model temperature (default: 0.7)

## 📊 Sample Data

The MVP includes sample inventory data in `data/inventory.csv`:

- 101: Laptop (5 in stock, reorder at 10)
- 102: Mouse (50 in stock, reorder at 20)
- 103: Keyboard (8 in stock, reorder at 15)
- 104: Monitor (12 in stock, reorder at 10)
- 105: USB Cable (100 in stock, reorder at 50)

## 🎓 Learning Objectives

This MVP demonstrates:

1. **LangGraph Multi-Agent Framework**
   - Inventory Monitor Agent (data loading → stock checking → recommendations)
   - Orchestrator Agent (user interaction → agent coordination)

2. **Model Context Protocol (MCP)**
   - Filesystem MCP server for reading CSV data
   - Abstraction layer for data access

3. **State Management**
   - Typed state models using TypedDict
   - State transitions through workflow nodes

4. **CLI Chat Interface**
   - Rich library for formatted output
   - Conversation history management

## 🚧 What's Next (Full Implementation)

The MVP can be extended with:

- 📊 Additional agents (Supplier Selector, Purchase Order)
- 🔗 A2A protocol for inter-agent communication
- 🤖 Deep Agents SDK (planning, sub-agents)
- 💾 Database MCP server (SQLite/PostgreSQL)
- 🌐 API MCP server (supplier integrations)
- ✋ Human-in-the-Loop (HITL) approval gates
- ✅ Comprehensive testing
- 📖 Full documentation

## 📝 Notes

- This is a learning MVP focused on core concepts
- Error handling is basic (will be enhanced in full version)
- No authentication or multi-user support yet
- No persistent storage beyond CSV files

## 🐛 Troubleshooting

**Issue: ModuleNotFoundError**
```bash
# Make sure you're in the project directory
cd c:\AgenticAI_Exp\SupplyChain

# Install dependencies
pip install -r requirements.txt
```

**Issue: API Key Error**
```bash
# Make sure .env file exists and has your API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your_key_here
```

**Issue: File Not Found**
```bash
# Make sure data/inventory.csv exists
ls data/inventory.csv
```

## 📚 Documentation

- [SYSTEM_UNDERSTANDING.md](SYSTEM_UNDERSTANDING.md) - Complete system design
- [PROGRESS.md](PROGRESS.md) - Implementation progress tracker

## 📄 License

This is a learning project for educational purposes.
