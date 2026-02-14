# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-Agent Quant Trader is a 2025 graduation design project implementing a **multi-agent AI quantitative trading system**. The system simulates institutional investment committee decision-making using specialized AI agents (Data Analyst, Risk Manager, Portfolio Manager) and combines LangGraph-based AI orchestration with high-performance C++ backtesting engines.

**Architecture Philosophy**: "Separation of computation and storage, software-hardware integration" (存算分离、软硬结合) - Python handles AI logic while C++ handles performance-critical operations.

## Technology Stack

- **Python 3.10** - Core language for AI/ML and web layers
- **C++17** - High-performance trading engine (planned, not yet implemented)
- **LangGraph/LangChain** - Multi-agent workflow orchestration
- **OpenAI API** - LLM models for intelligent decision-making
- **Flask + SocketIO** - Real-time web interface
- **ChromaDB** - Vector database for RAG (Retrieval-Augmented Generation)
- **Tushare** - Chinese financial data API
- **Pybind11** - Python-C++ bindings (planned)
- **SQLite** - Result storage and reasoning trace persistence

## Three-Layer Architecture

```
┌─────────────────────────────────────┐
│      Web Layer (Flask)            │  ← User interaction
│ - Chat Interface + Real-time UI    │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│    Service Layer (Python)          │  ← Multi-agent AI
│ - Handler Agent (coordinator)      │
│ - Data Service Agent (data fetcher) │
│ - Strategy Agent (strategy gen)     │
│ - Backtest Agent (testing)         │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│    Engine Layer (C++)              │  ← Performance (planned)
│ - Order Book + Portfolio Mgmt      │
│ - High-frequency matching engine    │
└─────────────────────────────────────┘
```

## Development Commands

### Initial Setup

**Create conda environment:**
```bash
conda create -n MAtrader python=3.10 -y
conda activate MAtrader
```

**Service Layer:**
```bash
cd src/service_layer
pip install -r requirements.txt
```

**Web Layer:**
```bash
cd src/web_layer
pip install -r requirements.txt
```

### Running the System

**Start Service Layer (self-test):**
```bash
cd src/service_layer
python main.py
```

**Start Web Layer:**
```bash
cd src/web_layer
python app.py
# Access at http://localhost:5000
```

### C++ Engine (Planned - Not Yet Implemented)
```bash
cd cpp_core
mkdir build && cd build
cmake ..
make
```

## Configuration Setup

**CRITICAL**: Before running, create `config/api_config.json`:

```json
{
  "tushare_api": "YOUR_TUSHARE_API_KEY",
  "model": {
    "handler_agent": {
      "model_name": "MODEL_NAME",
      "api_key": "YOUR_API_KEY",
      "base_url": "YOUR_BASE_URL"
    },
    "strategy_agent": {
      "model_name": "MODEL_NAME",
      "api_key": "YOUR_API_KEY",
      "base_url": "YOUR_BASE_URL"
    },
    "data_service_agent": {
      "model_name": "MODEL_NAME",
      "api_key": "YOUR_API_KEY",
      "base_url": "YOUR_BASE_URL"
    }
  }
}
```

- `config/prompt_config.json` - System prompts defining each agent's role
- `config/api_config.json` - API keys (not in git, must be created manually)

## Agent System Architecture

### Agent Workflow Pattern (LangGraph)

All agents follow the **LangGraph state machine pattern**:

1. **Input** → Receive `AgentState` (TypedDict) with context
2. **Analysis** → Parse intent and determine next actions
3. **Tool Execution** → Call tools or delegate to other agents
4. **State Update** → Modify shared state
5. **Output** → Return updated state to next node

**Key files:**
- `src/service_layer/agents/handler_agent.py` - Main coordinator
- `src/service_layer/agents/data_service_agent.py` - Data fetching tools
- `src/service_layer/agents/strategy_agent.py` - Strategy generation (new)
- `src/service_layer/agents/backtest_agent.py` - Backtesting logic (new)

### AgentState Structure

State passes between agents via a TypedDict containing:
- `messages`: Conversation history
- `next_agent`: Routing decision
- `extracted_data`: Structured data for inter-agent communication
- `reasoning_trace`: Decision-making audit trail

### Standardized Tool Output Format

**CRITICAL**: Data Service Agent MUST return this JSON structure for inter-agent compatibility:

```json
{
  "extracted_data": {
    "ts_code": "000001.SZ",
    "data_type": "daily",
    "count": 250,
    "data": [
      {
        "trade_date": "20240101",
        "open": 12.50,
        "high": 13.20,
        "low": 12.30,
        "close": 12.80,
        "vol": 1000000
      }
    ]
  }
}
```

This format is consumed by Strategy Agent and Backtest Agent.

## Data Service Agent Tools

Located in `src/service_layer/tools/`:

1. **`daily_data_tool.py`** - Daily K-line data (OHLCV)
2. **`adj_factor_tool.py`** - Adjustment factors for historical prices
3. **`daily_basic_tool.py`** - Basic metrics (PE, PB, market cap, turnover rate)

Tool registration pattern:
```python
# In agent initialization
tools = [
    get_daily_stock_data,
    get_adj_factor,
    get_daily_basic
]
```

## Key Entry Points

**Service Layer:**
- `src/service_layer/main.py` - Service layer entry point
- `src/service_layer/api/service.py` - API interface for web layer
- `src/service_layer/agents/handler_agent.py` - Core workflow orchestrator

**Web Layer:**
- `src/web_layer/app.py` - Flask application entry
- `src/web_layer/routes/main_routes.py` - Page routing
- `src/web_layer/routes/api_routes.py` - API endpoints

**Configuration:**
- `config/prompt_config.json` - Agent system prompts
- `config/api_config.json` - API keys (create manually)

## Important Development Patterns

### 1. Token Optimization
- **Message Manager** compresses conversation history to avoid token limits
- LangGraph checkpointing persists conversation state across sessions

### 2. Error Handling
- Graceful degradation when data services fail
- Comprehensive try-catch with logging
- Fallback mechanisms for AI judgment failures

### 3. Stock Code Format
- Shenzhen Exchange: `000001.SZ`
- Shanghai Exchange: `600000.SH`
- Date format: `YYYYMMDD` (e.g., `20240101`)

### 4. RAG Time Awareness
- ChromaDB vector searches MUST filter by simulation date
- Prevents data leakage (no future news visible to past decisions)

## Project Structure Notes

- `src/service_layer/strategy/` - Strategy definitions (new)
- `src/web_layer/Multi_Agent_Quant_Trader/` - Web UI build artifacts
- `doc/` - Design documentation (Chinese)
- `cpp_core/` - C++ engine (planned, not yet implemented)
- `tests/` - Test directory (newly created)

## Current Development Status

Based on git status, recent work includes:
- ✅ Adj factor and daily basic tools added
- ✅ Message manager and thinking status UI added
- ✅ Strategy Agent and Backtest Agent files created
- 🔄 C++ engine not yet implemented
- 🔄 Integration testing ongoing

## Testing Strategy

Run service layer self-test before committing changes:
```bash
cd src/service_layer
python main.py
```

Look for:
```
✅ Service层启动成功！
🎯 系统状态: healthy
```

## Common Gotchas

1. **API Config Missing**: System will fail to start if `config/api_config.json` doesn't exist
2. **Tushare Rate Limits**: Implement delays when fetching bulk data
3. **Token Limits**: Long conversations require Message Manager optimization
4. **Date Format Validation**: Always validate `YYYYMMDD` format before API calls
5. **Agent Coordination**: Don't bypass Handler Agent - all user requests flow through it first
