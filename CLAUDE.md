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

## Recent Updates (2026-02-15)

### Fixed Issues

#### 1. CSV Debug Output Added
Added CSV export to all 3 data tools (daily_data_tool, adj_factor_tool, daily_basic_tool) with automatic directory creation at `data/debug_csv/`

#### 2. Reduced Log Verbosity
Removed full data output from logs (handler_agent line 484-488, data_service_agent line 137-141), now only shows summaries and CSV file paths

#### 3. HandlerAgent Duplicate Execution (CRITICAL)
**Problem**: HandlerAgent was executing the entire workflow twice:
- First run: Normal full workflow
- Second run: Triggered by redundant `ainvoke()` in `process_message()` to save AI reply

**Root Cause**: Misunderstanding of LangGraph's checkpoint mechanism

**Solution** (handler_agent.py):
```python
# REMOVED this code (lines 631-639):
# if result.get("final_response") and not result.get("error"):
#     ai_message_state = {"messages": [AIMessage(content=ai_response_content)]}
#     await self.graph.ainvoke(ai_message_state, config=config)

# ADDED to _format_output_node:
state["messages"].append(AIMessage(content=str(response_content)))
```

**Key Insight**: LangGraph's checkpointer auto-saves state after each node. Just add AI reply to messages before END.

#### 2. Unified Data Format (CRITICAL)
**Problem**: Tools returned inconsistent formats:
- `daily_data_tool.py`: Returned `{"data": {...}}` dict
- `adj_factor_tool.py`: Returned JSON string
- `daily_basic_tool.py`: Returned JSON string

**Result**: Handler needed 100+ lines of parsing logic to handle multiple formats

**Solution**: Standardized all tools to return:

```python
{
    "success": True,
    "message": "成功获取...",
    "extracted_data": {
        "ts_code": "000001.SZ",
        "data_type": "daily",  # daily / adj_factor / daily_basic
        "count": 248,
        "data": [...]  # Actual data array
    }
}
```

**Files Modified**:
- `daily_data_tool.py` (line 193-205)
- `adj_factor_tool.py` (line 99-117)
- `daily_basic_tool.py` (line 108-126)
- `handler_agent.py` (_fetch_data_node simplified from 100+ lines to ~50 lines)
- `handler_agent.py` (_run_backtest_node simplified data reading)

**Lines of Code Reduced**: ~100 lines of redundant parsing logic removed

#### 3. Data Flow Clarification
**Before**: Complex nested parsing with multiple fallback paths
**After**: Direct single-path data access

```python
# Data flow:
Tool → {"extracted_data": {"data": [...]}} → Handler stores in state["fetched_data"]["data"]
                                                              ↓
                                              Backtest reads: state["fetched_data"]["data"]
```

## Known Issues (TODO)

### 1. Backtest Zero Trades (HIGH Priority)
**Symptom**:
```
总收益率: 0.00%
交易次数: 0  ← 关键问题
夏普比率: -46481426017038128.00  ← Division by zero/uninitialized
```

**Root Cause Chain**:

#### 2.1 Symbol Mismatch (Main Issue)
**Problem**: Strategy uses hardcoded symbol from example prompt
```python
# strategy_agent.py line 174 (example code in prompt)
symbol = '600000.SH'  # ❌ Hardcoded
```

**Actual Data**: `000001.SZ` (Ping An Bank)

**Result**: Strategy tries to `context.get_series('600000.SH', ...)` but data has `'000001.SZ'`, returns empty/no trades

#### 2.2 Dynamic Symbol Not Passed to LLM
**Problem**: `data_context` structure mismatch

**What's Passed** (handler_agent.py _generate_strategy_node):
```python
data_context = state.get("fetched_data")  # Contains: {ts_code, data, data_type, ...}
```

**What Strategy Agent Expects** (strategy_agent.py _build_strategy_prompt line 143):
```python
stock_info = data_context.get("stock_info", {})  # ← Doesn't exist in fetched_data!
```

**Result**: Prompt lacks stock code info, LLM falls back to hardcoded example value

#### 2.3 Sharpe Ratio Calculation Error
**File**: `src/service_layer/strategy/python_engine.py` line 330-331

**Problem**: When no trades, std(excess_returns) = 0, sharpe_ratio never gets calculated/initialized

**Fix Needed**: Initialize `BacktestResult.sharpe_ratio = 0.0` and handle zero-division

### 3. Architecture Notes

#### Center-Radiation Pattern is Valid
The HandlerAgent-centric architecture is CORRECT for LangGraph. The issue was:
- ❌ Incorrect: Manually re-invoking graph to save state
- ✅ Correct: Let LangGraph checkpoint auto-save, just update state["messages"]

**Valid Pattern**:
```
Handler → DataAgent → Handler → StrategyAgent → Handler → BacktestAgent → Handler → END
         ↑ returns to ↑          ↑ returns to ↑              ↑ returns to ↑
```

#### State Management Best Practice
```python
# DO: Modify state in nodes, let checkpoint handle persistence
state["messages"].append(AIMessage(content=response))

# DON'T: Re-invoke to save state
await graph.ainvoke({"messages": [...]})  # ← Triggers full workflow again!
```

## Recent Updates (2026-02-17)

### Fixed Issues

#### 1. Double Execution Completely Fixed (CRITICAL)
**Problem**: Even after fixing checkpoint, still had duplicate execution (1+ min apart, same conversation_id)

**Root Cause**: `handler_agent.py:604-612` had redundant `ainvoke()` call
```python
# This code re-triggered entire workflow:
if result.get("final_response"):
    ai_message_state = {"messages": [AIMessage(content=...)]}
    await self.graph.ainvoke(ai_message_state, config=config)  # ← Re-ran full workflow!
```

**Solution**: Deleted lines 604-612, already added AI reply to messages in `_format_output_node` (548-552)

**Files Modified**: `handler_agent.py` (process_message method)

#### 2. Frontend Anti-Duplicate-Submit Mechanism
**Added**: `isSending` flag to prevent rapid double-clicks (main.js:9, 266-271, 309, 343)

#### 3. Dynamic Field Injection into Strategy Prompt
**Problem**: LLM generated strategies using wrong field names (e.g., `volume` instead of `vol`)

**Solution**: Extract actual field names from fetched data and inject into prompt
```python
# strategy_agent.py:143-165
if data_context:
    data_list = extracted_data.get("data", [])
    if data_list:
        available_fields = list(data_list[0].keys())  # Extract from real data
        prompt += f"""
可用数据字段: {', '.join(available_fields)}
⚠️ 重要: vol (不是volume), amount (不是turnover)
"""
```

**Files Modified**: `strategy_agent.py` (_build_strategy_prompt method)

### Analysis Completed

**Strategy Flow Analysis** (2026-02-17):
1. ✅ Data passing: Handler → Engine → Context → Strategy (confirmed correct)
2. ✅ Framework compliance: Must inherit StrategyBase (enforced by code)
3. ✅ Bar shortage is valid: First 19 bars should be skipped (insufficient for 20-day MA)
4. ✅ Field mapping: Tushare returns `vol`/`amount` (not `volume`/`turnover`)

**Current Issues** (discussed, not yet fixed):
- Strategy lacks robust error handling for data shortage (throws IndexError on bars 0-19)
- Sharpe ratio shows extreme values when zero trades (division by zero)

## Development Priority

1. **HIGH**: Fix strategy robustness for data shortage (add try-except in on_bar)
2. **HIGH**: Fix Sharpe ratio calculation (handle zero-division)
3. **MEDIUM**: Add warmup_period mechanism to backtest engine
4. **LOW**: Add `is_data_ready()` helper method to SimpleContext
