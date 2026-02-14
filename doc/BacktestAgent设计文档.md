# BacktestAgent设计文档

## 设计概述

本文档定义了**中心辐射式**Agent协作架构，HandlerAgent作为中心枢纽，协调StrategyAgent、DataServiceAgent和BacktestAgent的协作。

### 核心理念
- **HandlerAgent**：中心枢纽，负责意图识别和流程控制
- **StrategyAgent**：策略专家，AI生成策略代码（独立Agent）
- **DataServiceAgent**：数据专家，提供历史数据（已存在）
- **BacktestAgent**：回测专家，执行回测和计算指标（独立Agent）
- **所有Agent独立**：各自在自己的文件中，通过HandlerAgent调用

### 实现阶段
- **阶段1（当前）**：StrategyAgent和BacktestAgent作为工具类
- **阶段2（未来）**：升级为独立Agent，添加工作流

---

## 架构设计

### Agent角色定位

| Agent | 类型 | 文件 | 状态 | 职责 |
|--------|------|------|------|------|
| **HandlerAgent** | 中心枢纽 | `src/service_layer/agents/handler_agent.py` | ✅ 已有 | 意图识别、流程控制、结果聚合 |
| **DataServiceAgent** | 数据专家 | `src/service_layer/agents/data_service_agent.py` | ✅ 已有 | 提供历史数据 |
| **StrategyAgent** | 策略专家 | `src/service_layer/agents/strategy_agent.py` | 🔴 待创建 | AI生成策略代码 |
| **BacktestAgent** | 回测专家 | `src/service_layer/agents/backtest_agent.py` | 🔴 待创建 | 执行回测、计算指标 |

### 完整数据流

```
用户: "用均线策略回测茅台2020-2024"
   ↓
┌─────────────────────────────────────────────────────────┐
│              HandlerAgent (中心枢纽)           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
            ┌───────────────────┐
            │ analyze_intent()   │
            │ 识别意图           │
            │ = "backtest_request"│
            └────────┬────────┘
                     │
        ┌──────────────────────┬─────────────┬──────────────────┐
        ↓                   ↓             ↓
   "fetch_data"      "generate_strategy" (调用)
        ↓                   ↓             ↓
   ┌───────────┐   ┌───────────────┐
   │DataServiceAgent│   │StrategyAgent  │
   └──────┬──────┘   └──────┬────────┘
        │                   │
        ↓                   ↓
   返回数据             返回策略代码
        │                   │
        └───────────┬────────┘
                   ↓
            ┌───────────────────┐
            │ HandlerAgent (聚合) │
            └──────┬──────────────┘
                   │
            保存数据到state
                   │
        └───────────┬────────┘
                   ↓
        ┌───────────────────┐
            │BacktestAgent (调用)│
            └──────┬──────────────┘
                   │
        传递策略代码+数据
                   │
        └───────────┬────────┘
                   ↓
            ┌───────────────────┐
            │ BacktestAgent执行 │
            │ - 加载策略代码 │
            │ - 加载数据    │
            │ - 运行回测     │
            │ - 计算指标     │
            └──────┬─────────────┘
                   │
                   ↓
            ┌───────────────────┐
            │返回回测结果       │
            └──────┬──────────────┘
                   │
                   ↓
            ┌───────────────────┐
            │HandlerAgent (格式化)│
            │ 生成最终回复      │
            └──────┬─────────────┘
                   ↓
              Web界面展示
```

---

## 文件结构

```
src/service_layer/agents/
├── __init__.py                          # 修改：导出新Agent
├── handler_agent.py                       # 修改：扩展工作流
├── data_service_agent.py                 # 已有：无需修改
├── message_manager.py                     # 已有：无需修改
└── [新增]
    ├── strategy_agent.py                    # 策略Agent（工具类）
    └── backtest_agent.py                  # 回测Agent（工具类）

src/service_layer/strategy/
├── __init__.py                           # 已有
├── strategy_base.py                       # 已有
├── simple_context.py                     # 已有
├── python_engine.py                      # 已有
└── examples/
    └── ma_strategy.py                      # 已有

tests/
└── [新增]
    └── agent/
        ├── test_strategy_agent.py
        └── test_backtest_agent.py
```

---

## StrategyAgent设计

### 文件
`src/service_layer/agents/strategy_agent.py`

### 类定义

```python
"""
StrategyAgent - 策略生成Agent

使用LLM根据用户需求生成交易策略代码
"""

from typing import Dict, Any, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config.config_manager import config_manager


class StrategyAgent:
    """
    策略生成Agent

    职责：
    - 根据用户需求生成策略代码
    - 支持多种策略类型（均线、RSI、MACD等）
    - 生成符合StrategyBase接口的代码
    """

    def __init__(self):
        """初始化StrategyAgent"""
        self.name = "strategy_agent"

        # 获取配置
        agent_config = config_manager.get_model_config("strategy_agent")
        self.llm = ChatOpenAI(
            model=agent_config["model_name"],
            openai_api_key=agent_config["api_key"],
            openai_api_base=agent_config["base_url"],
            temperature=0.3,  # 策略生成需要稳定
            max_tokens=2000
        )

        print(f"✅ StrategyAgent 初始化完成 - 模型: {agent_config['model_name']}")

    def generate_strategy(self,
                       user_request: str,
                       data_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        生成策略代码

        Args:
            user_request: 用户需求描述
            data_context: 数据上下文（可选，包含股票信息、市场数据等）

        Returns:
            {
                "success": True/False,
                "strategy_code": "策略Python代码",
                "strategy_name": "策略类名",
                "description": "策略描述",
                "error": "错误信息"（如果失败）
            }
        """
        try:
            print(f"\n🤖 生成交易策略...")
            print(f"📋 用户需求: {user_request}")

            # 构建提示词
            prompt = self._build_strategy_prompt(user_request, data_context)

            # 调用LLM生成
            print("🚀 开始调用LLM...")
            response = await self.llm.ainvoke([
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ])

            strategy_code = response.content.strip()

            # 提取代码（去除markdown标记）
            if "```python" in strategy_code:
                strategy_code = strategy_code.split("```python")[1].split("```")[0].strip()

            # 验证代码
            code_summary = self._validate_code(strategy_code)

            print(f"✅ 策略代码生成完成")
            print(f"📊 代码长度: {len(strategy_code)}字符")
            print(f"💭 代码预览:\n{code_summary[:200]}...")

            return {
                "success": True,
                "strategy_code": strategy_code,
                "strategy_name": self._extract_class_name(strategy_code),
                "description": f"根据需求生成的策略: {user_request[:50]}..."
            }

        except Exception as e:
            print(f"❌ 策略生成失败: {e}")
            return {
                "success": False,
                "error": f"策略生成失败: {str(e)}"
            }

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """
你是一个专业的量化策略设计师。请根据用户的需求生成Python交易策略代码。

策略代码要求：
1. 必须继承自StrategyBase类
2. 必须实现on_bar(self, context)方法
3. 使用context对象访问数据和下单：
   - context.get_bar(symbol, field, offset): 获取单根K线
   - context.get_series(symbol, field, count): 获取序列数据
   - context.buy(symbol, quantity, price): 下买单
   - context.sell(symbol, quantity, price): 下卖单
   - context.get_cash(): 获取可用资金
   - context.get_position(symbol): 获取持仓
4. 策略逻辑清晰，有适当注释
5. 处理边界情况（数据不足返回None）

策略类型参考：
- 均线策略：MA、EMA、双均线金叉死叉
- 动量指标：RSI、MACD、KDJ
- 价格形态：突破、反转、形态识别
- 量价策略：成交量突破、缩量上涨

只输出Python代码，不要markdown标记，不要任何文字说明。
"""

    def _build_strategy_prompt(self, user_request: str, data_context: Optional[Dict]) -> str:
        """构建策略生成提示词"""

        prompt = f"""
用户需求: {user_request}
"""

        # 如果有数据上下文，添加到prompt
        if data_context:
            stock_info = data_context.get("stock_info", {})
            if stock_info:
                prompt += f"""

股票信息:
- 代码: {stock_info.get('code', 'N/A')}
- 名称: {stock_info.get('name', 'N/A')}
- 时间范围: {data_context.get('date_range', 'N/A')}
"""

        prompt += """

请生成对应的交易策略代码。策略应该清晰、可执行、有良好的注释。

示例格式（均线金叉策略）:
"""
        # 示例代码
        prompt += """
class MAStrategy(StrategyBase):
    def __init__(self, short=5, long=20):
        super().__init__()
        self.short = short
        self.long = long

    def on_bar(self, context):
        short_ma = sum(context.get_series('600000.SH', 'close', self.short)) / self.short
        long_ma = sum(context.get_series('600000.SH', 'close', self.long)) / self.long

        if short_ma > long_ma and context.get_cash() > 0:
            return {
                'action': 'buy',
                'symbol': '600000.SH',
                'quantity': 100,
                'price': context.get_bar('600000.SH', 'close', 0)
            }
        elif short_ma < long_ma and context.get_position('600000.SH') > 0:
            return {
                'action': 'sell',
                'symbol': '600000.SH',
                'quantity': -context.get_position('600000.SH'),
                'price': context.get_bar('600000.SH', 'close', 0)
            }
        return None
"""

        return prompt

    def _validate_code(self, code: str) -> str:
        """验证策略代码"""
        lines = code.split('\n')
        summary = []

        # 检查关键元素
        if 'class ' in code:
            class_name = [line for line in lines if 'class' in line][0]
            summary.append(f"✅ 策略类: {class_name}")

        if 'def on_bar' in code:
            summary.append("✅ 实现了on_bar方法")

        if 'context.buy' in code or 'context.sell' in code:
            summary.append("✅ 使用了交易接口")

        return '\n'.join(summary)

    def _extract_class_name(self, code: str) -> str:
        """从代码中提取类名"""
        import re
        match = re.search(r'class\s+(\w+)', code)
        return match.group(1) if match else "GeneratedStrategy"
```

---

## BacktestAgent设计

### 文件
`src/service_layer/agents/backtest_agent.py`

### 类定义

```python
"""
BacktestAgent - 回测执行Agent

负责执行回测、计算绩效指标
"""

from typing import Dict, Any, Optional, List

from ..strategy import PythonBacktestEngine, BacktestResult
from ..strategy.examples.ma_strategy import MAStrategy


class BacktestAgent:
    """
    回测Agent

    职责：
    - 加载策略代码
    - 执行回测
    - 计算绩效指标
    - 返回格式化结果
    """

    def __init__(self):
        """初始化BacktestAgent"""
        self.name = "backtest_agent"
        self.engine = None
        self.strategy = None
        print(f"✅ BacktestAgent 初始化完成")

    def run_backtest(self,
                       strategy_code: str,
                       data: List[Dict]) -> Dict[str, Any]:
        """
        执行回测

        Args:
            strategy_code: 策略Python代码
            data: K线数据列表

        Returns:
            {
                "success": True/False,
                "result": BacktestResult.to_dict(),
                "summary": "回测结果摘要",
                "error": "错误信息"
            }
        """
        try:
            print(f"\n⚙️  开始执行回测...")
            print(f"📊 数据量: {len(data)} 根K线")

            # ========== 步骤1: 加载策略代码 ==========
            strategy = self._load_strategy_from_code(strategy_code)
            if strategy is None:
                return {
                    "success": False,
                    "error": "策略代码加载失败"
                }

            print("✅ 策略代码加载完成")

            # ========== 步骤2: 创建回测引擎 ==========
            self.engine = PythonBacktestEngine(
                initial_capital=1000000.0,
                commission_rate=0.0003,
                slippage_rate=0.0001
            )

            # ========== 步骤3: 注册并初始化 ==========
            self.engine.register_strategy(strategy)
            self.engine.init(data)

            print("✅ 回测引擎初始化完成")

            # ========== 步骤4: 执行回测 ==========
            result = self.engine.run()

            # ========== 步骤5: 格式化结果 ==========
            summary = self._format_summary(result)

            print(f"✅ 回测执行完成")
            print(f"\n{summary}")

            return {
                "success": True,
                "result": result.to_dict(),
                "summary": summary
            }

        except Exception as e:
            print(f"❌ 回测执行失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"回测执行失败: {str(e)}"
            }

    def _load_strategy_from_code(self, code: str) -> Optional[object]:
        """
        从代码字符串加载策略类

        Args:
            code: 策略Python代码

        Returns:
            策略实例，如果加载失败返回None
        """
        try:
            # 创建命名空间
            namespace = {}

            # 执行代码
            exec(code, namespace)

            # 查找策略类
            strategy_class = None
            for key, value in namespace.items():
                if isinstance(value, type) and issubclass(value, object):
                    from ..strategy.strategy_base import StrategyBase
                    if issubclass(value, StrategyBase):
                        strategy_class = value
                        break

            if strategy_class is None:
                print("❌ 未找到策略类，代码可能不符合StrategyBase接口")
                return None

            # 创建策略实例
            strategy = strategy_class()

            # 验证必要方法
            if not hasattr(strategy, 'on_bar'):
                print("❌ 策略类缺少on_bar方法")
                return None

            print(f"✅ 成功加载策略类: {strategy.__class__.__name__}")
            return strategy

        except Exception as e:
            print(f"❌ 策略代码加载失败: {e}")
            return None

    def _format_summary(self, result: BacktestResult) -> str:
        """
        格式化回测结果摘要
        """
        return f"""
=== 回测结果 ===
📈 总收益率: {result.total_return:.2%}
📅 年化收益率: {result.annual_return:.2%}
⚡ 夏普比率: {result.sharpe_ratio:.2f}
📉 最大回撤: {result.max_drawdown:.2%}
🎯 胜率: {result.win_rate:.2%}
💹 交易次数: {result.total_trades}
💰 平均每笔收益: {result.avg_profit_per_trade:.2f}
📊 盈亏比: {result.profit_loss_ratio:.2f}
==================
"""
```

---

## HandlerAgent扩展

### 需要修改的文件
`src/service_layer/agents/handler_agent.py`

### 修改1：导入新Agent

```python
# 在文件开头添加导入
from .strategy_agent import strategy_agent
from .backtest_agent import backtest_agent
```

### 修改2：扩展意图识别

```python
async def _analyze_intent_node(self, state: AgentState) -> AgentState:
    """意图分析节点（扩展版）"""
    try:
        print("🧠 分析用户意图...")
        state["current_step"] = "analyzing_intent"

        user_input = state["user_input"].lower()

        # 意图类型识别（扩展）
        if any(keyword in user_input for keyword in ["回测", "策略", "收益", "夏普", "绩效"]):
            intent = "backtest_request"
        elif any(keyword in user_input for keyword in ["选股", "筛选", "分析", "数据"]):
            intent = "data_analysis"
        elif any(keyword in user_input for keyword in ["风险", "回撤", "波动"]):
            intent = "risk_analysis"
        else:
            intent = "general_question"

        state["analysis_result"] = intent
        print(f"🎯 识别意图: {intent}")

        return state

    except Exception as e:
        print(f"❌ 意图分析失败: {e}")
        state["error"] = f"意图分析失败: {str(e)}"
        return state
```

### 修改3：扩展工作流图

```python
def _build_graph(self) -> StateGraph:
    """构建LangGraph工作流（扩展版）"""
    workflow = StateGraph(AgentState)

    # 添加节点（原有）
    workflow.add_node("parse_input", self._parse_input_node)
    workflow.add_node("analyze_intent", self._analyze_intent_node)
    workflow.add_node("check_data_need", self._check_data_need_node)
    workflow.add_node("fetch_data", self._fetch_data_node)
    workflow.add_node("generate_response", self._generate_response_node)
    workflow.add_node("format_output", self._format_output_node)

    # 添加节点（新增）
    workflow.add_node("generate_strategy", self._generate_strategy_node)  # 新增！
    workflow.add_node("run_backtest", self._run_backtest_node)  # 新增！

    # 定义流程
    workflow.add_edge(START, "parse_input")
    workflow.add_edge("parse_input", "analyze_intent")
    workflow.add_edge("analyze_intent", "check_data_need")

    # 条件分支1：是否需要数据
    workflow.add_conditional_edges(
        "check_data_need",
        self._should_fetch_data,
        {
            "fetch_data": "fetch_data",
            "generate_response": "generate_response"
        }
    )

    # 条件分支2：数据获取后路由（核心！）
    workflow.add_conditional_edges(
        "fetch_data",
        self._route_after_data,  # 新增路由函数
        {
            "backtest": "generate_strategy",  # 回测分支
            "analysis": "generate_response"  # 分析分支
        }
    )

    # 回测链路
    workflow.add_edge("generate_strategy", "run_backtest")
    workflow.add_edge("run_backtest", "generate_response")

    # 分析流程（直接生成回复）
    workflow.add_edge("analysis", "generate_response")

    # 原有路径
    workflow.add_edge("generate_response", "format_output")
    workflow.add_edge("format_output", END)

    return workflow.compile(checkpointer=self.checkpointer)
```

### 修改4：新增节点

```python
async def _route_after_data(self, state: AgentState) -> str:
    """数据获取完成后的路由（核心）"""
    intent = state.get("analysis_result")

    print(f"🎯 路由决策: 意图={intent}")

    if intent == "backtest_request":
        return "generate_strategy"
    else:
        return "generate_response"

async def _generate_strategy_node(self, state: AgentState) -> AgentState:
    """生成策略节点（新增）"""
    try:
        print("🤖 生成交易策略...")
        state["current_step"] = "generating_strategy"

        user_input = state["user_input"]

        # 调用StrategyAgent生成策略
        result = await strategy_agent.generate_strategy(
            user_request=user_input,
            data_context=state.get("fetched_data")
        )

        if result["success"]:
            state["strategy_code"] = result["strategy_code"]
            state["strategy_name"] = result["strategy_name"]
            print(f"✅ 策略代码生成完成")
        else:
            state["error"] = result.get("error", "策略生成失败")

        return state

    except Exception as e:
        print(f"❌ 策略生成失败: {e}")
        state["error"] = f"策略生成异常: {str(e)}"
        return state

async def _run_backtest_node(self, state: AgentState) -> AgentState:
    """回测执行节点（新增）"""
    try:
        print("⚙️  执行回测...")
        state["current_step"] = "running_backtest"

        # 获取策略代码和数据
        strategy_code = state.get("strategy_code")
        data = state.get("fetched_data", {}).get("data")

        if not strategy_code:
            raise ValueError("缺少策略代码")

        if not data:
            raise ValueError("缺少历史数据")

        # 调用BacktestAgent执行回测
        result = backtest_agent.run_backtest(
            strategy_code=strategy_code,
            data=data
        )

        if result["success"]:
            state["backtest_result"] = result["result"]
            state["backtest_summary"] = result["summary"]
            print(f"✅ 回测完成: {result['summary'][:100]}")
        else:
            state["error"] = result.get("error", "回测失败")

        return state

    except Exception as e:
        print(f"❌ 回测执行失败: {e}")
        state["error"] = f"回测执行异常: {str(e)}"
        return state
```

### 修改5：更新AgentState

```python
class AgentState(TypedDict):
    """Agent状态定义（扩展版）"""
    messages: Annotated[List, add_messages]
    user_input: str
    conversation_id: str
    current_step: str
    analysis_result: Optional[str]
    needs_data: Optional[bool]
    data_request: Optional[str]
    fetched_data: Optional[Dict[str, Any]]  # 新增：获取的数据

    # 回测相关（新增）
    strategy_code: Optional[str]  # 新增：生成的策略代码
    strategy_name: Optional[str]  # 新增：策略类名
    backtest_result: Optional[Dict]  # 新增：回测结果
    backtest_summary: Optional[str]  # 新增：回测摘要

    final_response: Optional[str]
    error: Optional[str]
```

### 修改6：扩展生成响应节点

```python
async def _generate_response_node(self, state: AgentState) -> AgentState:
    """生成回复节点（扩展版）"""
    try:
        print("✨ 生成AI回复...")
        state["current_step"] = "generating_response"

        intent = state.get("analysis_result", "general_question")

        # 如果有回测结果，优先展示
        if intent == "backtest_request" and "backtest_summary" in state:
            summary = state["backtest_summary"]

            # 简化：直接使用预格式化的摘要
            response_content = f"""
{summary}

💡 提示：
- 可以尝试调整策略参数（均线周期、止盈止损）
- 可以对比不同策略的表现
- 历史数据仅供参考，不构成投资建议
"""
            state["final_response"] = {
                "content": response_content,
                "timestamp": datetime.now().isoformat(),
                "intent": intent,
                "conversation_id": state.get("conversation_id", ""),
                "agent": "handler_agent",
                "type": "backtest_result"
            }

            print(f"💬 回测结果生成完成")
            return state

        # 原有的逻辑：普通AI回复
        intent = state.get("analysis_result", "general_question")

        if intent == "investment_analysis":
            system_prompt = """你是一个专业的投资分析师。请基于用户的问题和之前的对话历史提供专业的投资建议和分析。
重点关注：基本面分析、技术面分析、市场趋势、投资风险等方面。请根据对话历史保持上下文连贯性。"""
        elif intent == "risk_analysis":
            system_prompt = """你是一个专业的风险管理专家。请重点分析投资风险，包括：
市场风险、信用风险、流动性风险、操作风险等，并提供风险控制建议。请根据对话历史保持上下文连贯性。"""
        else:
            system_prompt = """你是一个友好的AI助手，专注于金融投资领域。
请根据用户问题和之前的对话历史提供有用的信息和建议，保持对话的连贯性。"""

        # 构建消息列表 - 使用MessageManager优化消息历史
        raw_messages = [SystemMessage(content=system_prompt)] + state["messages"]

        # 使用MessageManager优化消息列表
        optimized_messages = self.message_manager.optimize_messages(raw_messages)

        # 调试输出：显示优化后的消息统计
        stats = self.message_manager.get_stats(optimized_messages)
        print(f"📊 消息统计: {stats['total_messages']}条消息, {stats['total_tokens']}个tokens")
        print(f"   👤用户: {stats['user_messages']}条, 🤖AI: {stats['ai_messages']}条, ⚙️系统: {stats['system_messages']}条")

        if len(optimized_messages) > 1:
            print(f"💭 检测到历史对话，将基于优化后的上下文生成回复")

        # 使用优化后的消息列表
        messages = optimized_messages

        print(f"🚀 开始调用模型...")

        # 直接使用LangChain的ChatOpenAI调用
        response = await self.llm.ainvoke(messages)
        response_content = response.content

        state["final_response"] = response_content
        print(f"💬 生成回复完成，长度: {len(response_content)}")

        return state

    except Exception as e:
        print(f"❌ 回复生成失败: {e}")
        state["error"] = f"回复生成失败: {str(e)}"
        return state
```

---

## __init__.py 更新

```python
"""
Agents模块初始化
"""

from .handler_agent import handler_agent
from .data_service_agent import data_service_agent
from .message_manager import message_manager

# 新增导出
from .strategy_agent import strategy_agent
from .backtest_agent import backtest_agent

__all__ = [
    'handler_agent',
    'data_service_agent',
    'message_manager',
    'strategy_agent',    # 新增
    'backtest_agent'     # 新增
]
```

---

## 完整数据流

### 场景1：回测流程

```
用户: "用均线策略回测茅台2020-2024"
   ↓
HandlerAgent.analyze_intent()
   - 识别: intent = "backtest_request"
   ↓
HandlerAgent.check_data_need()
   - 判断: needs_data = YES
   ↓
HandlerAgent.fetch_data()
   - handler_instruction: "获取茅台数据..."
   - 调用: data_service_agent.think_and_respond()
   - 返回: {"success": True, "content": "...500根K线数据..."}
   ↓
HandlerAgent (保存数据到state)
   - state["fetched_data"] = {"data": [...]}
   ↓
HandlerAgent._route_after_data()
   - 判断: intent = "backtest_request"
   - 返回: "generate_strategy"
   ↓
HandlerAgent._generate_strategy_node()
   - 调用: strategy_agent.generate_strategy(user_request)
   - LLM生成策略代码
   - 返回: {"strategy_code": "class MAStrategy...", "success": True}
   - 保存: state["strategy_code"] = "..."
   ↓
HandlerAgent._run_backtest_node()
   - 获取: strategy_code, data
   - 调用: backtest_agent.run_backtest(strategy_code, data)
   - 执行回测，计算指标
   - 返回: {"result": {...}, "summary": "...", "success": True}
   - 保存: state["backtest_result"] = {...}
   ↓
HandlerAgent._generate_response_node()
   - 检测到: intent = "backtest_request" and "backtest_summary" 存在
   - 生成回复: 包含回测摘要
   - 返回给Web界面
```

### 场景2：数据分析

```
用户: "茅台最近走势如何？"
   ↓
HandlerAgent.analyze_intent()
   - 识别: intent = "data_analysis"
   ↓
HandlerAgent.check_data_need()
   - 判断: needs_data = YES
   ↓
HandlerAgent.fetch_data()
   - handler_instruction: "获取茅台数据..."
   - 调用: data_service_agent.think_and_respond()
   - 返回数据分析
   ↓
HandlerAgent._generate_response_node()
   - intent = "data_analysis"
   - LLM生成分析回复
   - 返回给Web界面
```

### 场景3：普通问答

```
用户: "什么是夏普比率？"
   ↓
HandlerAgent.analyze_intent()
   - 识别: intent = "general_question"
   ↓
HandlerAgent.check_data_need()
   - 判断: needs_data = NO
   ↓
HandlerAgent._generate_response_node()
   - intent = "general_question"
   - LLM生成回复
   - 返回给Web界面
```

---

## 测试策略

### 单元测试

| 测试项 | 文件 | 说明 |
|--------|------|------|
| StrategyAgent代码生成 | `tests/agent/test_strategy_agent.py` | 测试LLM生成 |
| BacktestAgent回测执行 | `tests/agent/test_backtest_agent.py` | 测试回测流程 |
| HandlerAgent工作流 | `tests/agent/test_handler_integration.py` | 测试完整链路 |

### 测试示例

```python
# tests/agent/test_strategy_agent.py

import asyncio
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.service_layer.agents.strategy_agent import StrategyAgent


async def test_strategy_generation():
    """测试策略生成"""
    print("=" * 60)
    print("测试1: 策略生成")
    print("=" * 60)

    agent = StrategyAgent()

    # 测试1：简单请求
    result1 = await agent.generate_strategy(
        user_request="生成一个双均线策略"
    )

    assert result1["success"] == True
    assert "strategy_code" in result1
    assert "class " in result1["strategy_code"]
    print(f"✅ 测试1通过")

    # 测试2：带数据上下文的请求
    result2 = await agent.generate_strategy(
        user_request="为茅台设计均线策略",
        data_context={
            "stock_info": {"code": "600519.SH", "name": "贵州茅台"},
            "date_range": ("20230101", "20241231")
        }
    )

    assert result2["success"] == True
    print(f"✅ 测试2通过")

    print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    asyncio.run(test_strategy_generation())
```

---

## 错误处理

### 异常处理策略

1. **StrategyAgent错误**
   - LLM调用失败 → 返回友好提示，建议重试
   - 代码验证失败 → 使用默认策略
   - 超时 → 设置合理的超时

2. **BacktestAgent错误**
   - 策略代码加载失败 → 返回详细错误
   - 数据不足 → 返回友好提示
   - 回测执行失败 → 记录详细日志

3. **HandlerAgent错误**
   - Agent调用失败 → 记录错误，降级处理
   - State异常 → 尝试恢复或清理

---

## 实施优先级

### 阶段1：基础Agent（1-2天）

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 创建StrategyAgent | `strategy_agent.py` | 🔴 高 |
| 创建BacktestAgent | `backtest_agent.py` | 🔴 高 |
| 修改HandlerAgent导入 | `__init__.py` | 🔴 高 |
| 修改HandlerAgent意图识别 | `handler_agent.py` | 🔴 高 |
| 添加新工作流节点 | `handler_agent.py` | 🔴 高 |
| 扩展AgentState | `handler_agent.py` | 🔴 高 |
| 更新生成响应节点 | `handler_agent.py` | 🔴 高 |

### 阶段2：单元测试（1天）

| 任务 | 优先级 |
|------|--------|
| 测试StrategyAgent | 🔴 高 |
| 测试BacktestAgent | 🔴 高 |
| 集成测试 | 🟡 中 |

### 阶段3：文档更新（30分钟）

| 任务 | 优先级 |
|------|--------|
| 更新设计文档 | 🟢 低 |
| 更新README | 🟢 低 |

---

## 扩展性设计

### 未来扩展方向

1. **多Agent协作**
   - RiskAgent：风险评估
   - PortfolioAgent：投资组合管理
   - 所有Agent通过HandlerAgent协调

2. **策略库**
   - 预设策略模板
   - 策略参数优化
   - 策略组合对比

3. **高级回测**
   - 参数扫描
   - 参数优化（遗传算法、网格搜索）
   - Walk-Forward分析

4. **可视化增强**
   - 交互式K线图
   - 实时回测
   - 策略分析图

---

## 总结

### 核心特点

1. ✅ **中心辐射式架构**：HandlerAgent作为中心枢纽
2. ✅ **职责清晰**：每个Agent专注自己的领域
3. ✅ **易于扩展**：新增Agent只需修改HandlerAgent
4. ✅ **完全独立**：StrategyAgent和BacktestAgent独立文件
5. ✅ **数据传递**：通过state传递（合理，数据量不大）
6. ✅ **符合现有架构**：遵循DataServiceAgent模式

### 关键设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| Agent文件 | 独立文件 | 职责清晰，易于维护 |
| 数据传递 | 通过state | 日K线数据量不大，合理 |
| 实现阶段 | 先工具类，后Agent | 快速验证，后续升级 |
| 路由控制 | HandlerAgent中心 | 全局可见，易于调试 |
