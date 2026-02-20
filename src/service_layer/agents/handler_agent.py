"""
HandlerAgent 核心实现
使用LangGraph框架构建的主控Agent
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver as InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict

from ..config.config_manager import config_manager
from .message_manager import MessageManager
from .data_service_agent import data_service_agent
from .strategy_agent import strategy_agent
from .backtest_agent import backtest_agent

class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[List, add_messages]
    user_input: str
    conversation_id: str
    current_step: str
    analysis_result: Optional[str]
    needs_data: Optional[bool]
    data_request: Optional[str]
    fetched_data: Optional[Dict[str, Any]]

    # 回测相关
    strategy_code: Optional[str]  # 新增：生成的策略代码
    strategy_name: Optional[str]  # 新增：策略类名
    user_confirmed_backtest: Optional[bool]  # 新增：用户是否确认执行回测
    backtest_result: Optional[Dict]  # 新增：回测结果
    backtest_summary: Optional[str]  # 新增：回测摘要

    final_response: Optional[str]
    error: Optional[str]

class HandlerAgent:
    """主控Agent - 系统的大脑和指挥官"""
    
    def __init__(self):
        """初始化HandlerAgent"""
        # Agent名称
        self.name = "handler_agent"
        
        # 获取配置信息
        print(self.name)
        agent_config = config_manager.get_model_config(self.name)
        self.llm = ChatOpenAI(
            model=agent_config["model_name"],
            openai_api_key=agent_config["api_key"],
            openai_api_base=agent_config["base_url"],
            temperature=0.7
        )
        # 初始化内存checkpointer
        self.checkpointer = InMemorySaver()
        
        # 获取系统提示词
        self.system_prompt = config_manager.get_prompt_config(self.name)
        
        # 初始化消息管理器
        self.message_manager = MessageManager()
        
        self.graph = self._build_graph()
        print(f"✅ HandlerAgent 初始化完成 - 模型: {agent_config['model_name']}")
    
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
        workflow.add_node("generate_strategy", self._generate_strategy_node)
        workflow.add_node("run_backtest", self._run_backtest_node)

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

        # 条件分支2：数据获取后路由
        workflow.add_conditional_edges(
            "fetch_data",
            self._route_after_data,
            {
                "generate_strategy": "generate_strategy",  # 回测分支
                "generate_response": "generate_response"  # 分析分支
            }
        )

        # 回测链路：生成策略后需要用户确认才执行回测
        # 使用条件边：如果state中有user_confirmed_backtest=True才执行回测，否则结束
        workflow.add_conditional_edges(
            "generate_strategy",
            self._should_run_backtest,
            {
                "run_backtest": "run_backtest",
                "end": "generate_response"  # 用户未确认，直接生成说明并结束
            }
        )

        workflow.add_edge("run_backtest", "generate_response")
        workflow.add_edge("generate_response", "format_output")
        workflow.add_edge("format_output", END)

        return workflow.compile(checkpointer=self.checkpointer)
    
    async def _parse_input_node(self, state: AgentState) -> AgentState:
        """解析输入节点"""
        try:
            print(f"📥 解析用户输入: {state['user_input'][:50]}...")
            
            # 更新状态
            state["current_step"] = "parsing_input"
            state["messages"] = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=state["user_input"])
            ]
            
            return state
            
        except Exception as e:
            print(f"❌ 输入解析失败: {e}")
            state["error"] = f"输入解析失败: {str(e)}"
            return state
    
    async def _analyze_intent_node(self, state: AgentState) -> AgentState:
        """意图分析节点"""
        try:
            print("🧠 分析用户意图...")
            state["current_step"] = "analyzing_intent"
            
            # 这里可以添加更复杂的意图分析逻辑
            # 目前先做简单的关键词分析
            user_input = state["user_input"].lower()

            if any(keyword in user_input for keyword in ["回测", "策略", "收益", "夏普", "绩效"]):
                intent = "backtest_request"
            elif any(keyword in user_input for keyword in ["股票", "投资", "分析"]):
                intent = "investment_analysis"
            elif any(keyword in user_input for keyword in ["风险", "回撤", "波动"]):
                intent = "risk_analysis"
            elif any(keyword in user_input for keyword in ["选股", "筛选", "数据"]):
                intent = "data_analysis"
            else:
                intent = "general_question"
            
            state["analysis_result"] = intent
            print(f"🎯 识别意图: {intent}")
            
            return state
            
        except Exception as e:
            print(f"❌ 意图分析失败: {e}")
            state["error"] = f"意图分析失败: {str(e)}"
            return state
    
    async def _check_data_need_node(self, state: AgentState) -> AgentState:
        """智能检查是否需要数据节点"""
        try:
            print("🤖 AI智能判断是否需要获取数据...")
            state["current_step"] = "checking_data_need"
            
            # 先检查用户意图，对于回测请求强制需要数据
            intent = state.get("analysis_result", "")
            
            if intent == "backtest_request":
                # 回测请求必须获取数据，传递用户原始输入让DataServiceAgent解析
                print("🎯 检测到回测请求，强制获取数据")
                state["needs_data"] = True
                state["data_request"] = state["user_input"]  # 传递原始输入
                return state
            
            # 构建AI判断提示词
            judge_prompt = f"""
你是一个专业的投资分析助手。请判断用户的以下问题是否需要获取实时股票数据来进行回答。

用户问题："{state['user_input']}"

判断标准：
1. 如果问题涉及具体股票的价格、行情、K线数据、技术分析等，需要数据
2. 如果问题涉及某只股票的历史表现、走势分析等，需要数据  
3. 如果问题涉及策略回测、生成策略等，需要数据
4. 如果是一般性的投资理论、概念解释等，不需要数据
5. 如果是问候、介绍等日常对话，不需要数据

请只回答"YES"（需要数据）或"NO"（不需要数据），并简要说明理由。

回答格式：
判断：YES/NO
理由：[简要说明]
数据需求：[如果需要数据，说明需要什么类型的数据]
"""
            
            # 调用AI进行判断
            judge_message = [SystemMessage(content=judge_prompt)]
            response = await self.llm.ainvoke(judge_message)
            judge_result = response.content
            
            print(f"🧠 AI判断结果: {judge_result}")
            
            # 解析AI的判断结果
            needs_data = "YES" in judge_result.upper()
            state["needs_data"] = needs_data
            
            if needs_data:
                state["data_request"] = state["user_input"]
                print(f"📊 AI判断需要获取数据")
            else:
                print("💭 AI判断不需要获取数据，直接生成回复")
            
            # 将AI判断结果添加到状态中，供调试使用
            state["ai_judgment"] = judge_result
            
            return state
            
        except Exception as e:
            print(f"❌ AI数据需求判断失败: {e}")
            # 如果AI判断失败，回退到安全的关键词检查
            print("🔄 回退到关键词检查模式...")
            user_input = state["user_input"].lower()
            data_keywords = ["股票", "股价", "行情", "k线", "价格", "涨跌", "000001", "600000"]
            needs_data = any(keyword in user_input for keyword in data_keywords)
            state["needs_data"] = needs_data
            state["data_request"] = state["user_input"] if needs_data else ""
            return state
    
    def _should_fetch_data(self, state: AgentState) -> str:
        """判断是否应该获取数据的条件函数"""
        needs_data = state.get("needs_data", False)
        print(f"🎯 路由决策: {'获取数据' if needs_data else '直接回复'}")
        return "fetch_data" if needs_data else "generate_response"

    def _route_after_data(self, state: AgentState) -> str:
        """数据获取完成后的路由（核心）"""
        intent = state.get("analysis_result")

        print(f"🎯 路由决策: 意图={intent}")

        if intent == "backtest_request":
            return "generate_strategy"
        else:
            return "generate_response"

    def _should_run_backtest(self, state: AgentState) -> str:
        """判断是否应该执行回测的条件函数"""
        # 检查用户是否确认了回测
        user_confirmed = state.get("user_confirmed_backtest", False)

        print(f"🎯 回测决策: {'用户已确认，执行回测' if user_confirmed else '等待用户确认'}")

        return "run_backtest" if user_confirmed else "end"

    async def _fetch_data_node(self, state: AgentState) -> AgentState:
        """数据获取节点"""
        try:
            print("📈 开始获取数据...")
            state["current_step"] = "fetching_data"
            
            data_request = state.get("data_request", "")
            conversation_id = state.get("conversation_id", "")
            
            # 调用DataServiceAgent获取数据
            print(f"🔌 调用DataServiceAgent...")
            data_result = await data_service_agent.think_and_respond(
                handler_instruction=data_request,
                conversation_id=conversation_id
            )
            
            if data_result["success"]:
                # 提取中间步骤中的工具输出（实际的数据）
                intermediate_steps = data_result.get("intermediate_steps", [])

                # 修复：intermediate_steps是tuple列表，需要正确解析
                print(f"🔍 调试: intermediate_steps类型={type(intermediate_steps)}, 长度={len(intermediate_steps)}")
                
                # 从工具输出中提取实际数据
                data = None
                for i, step in enumerate(intermediate_steps):
                    print(f"🔍 步骤{i}: 类型={type(step)}")

                    # step是tuple: (AgentAction, observation)
                    if isinstance(step, tuple) and len(step) == 2:
                        action, observation = step
                        tool_name = getattr(action, 'tool', 'unknown')
                        print(f"🔍 步骤{i}: 工具={tool_name}")

                        # 🔍 调试：打印observation结构
                        print(f"🔍 observation类型: {type(observation)}")
                        if isinstance(observation, dict):
                            print(f"🔍 observation键: {list(observation.keys())}")

                        # 统一解析：所有工具都返回 {"success": True, "extracted_data": {...}}
                        if isinstance(observation, dict):
                            if "extracted_data" in observation:
                                extracted_data = observation["extracted_data"]
                                data = extracted_data.get("data")
                                data_type = extracted_data.get("data_type")
                                ts_code = extracted_data.get("ts_code")

                                if isinstance(data, list) and len(data) > 0:
                                    print(f"✅ 从{tool_name}提取到 {len(data)} 条{data_type}数据")
                                    print(f"   股票代码: {ts_code}")
                                    break
                                else:
                                    print(f"⚠️ {tool_name}返回的数据为空或格式错误: {type(data)}")
                            else:
                                print(f"⚠️ {tool_name}返回格式缺少extracted_data字段")
                        else:
                            print(f"⚠️ {tool_name}返回的不是字典格式: {type(observation)}")

                print(f"📊 最终提取到的数据: {len(data) if data else 0} 条K线")

                # 保存原始data_result用于调试
                state["fetched_data"] = {
                    **data_result,
                    "data": data  # 实际的K线数据列表
                }

                # 将数据信息添加到消息中，供后续生成回复使用
                data_content = data_result.get('content', '')
                if len(data_content) > 500:
                    data_summary = data_content[:500] + "..."
                else:
                    data_summary = data_content

                data_message = f"\n[💰 已获取到相关数据]: {data_summary}"
                state["messages"].append(SystemMessage(content=data_message))
                
            else:
                print(f"⚠️ 数据获取失败: {data_result['message']}")
                state["fetched_data"] = data_result
                error_msg = f"\n[⚠️ 数据服务提示]: {data_result['message']}"
                state["messages"].append(SystemMessage(content=error_msg))
            
            return state

        except Exception as e:
            print(f"❌ 数据获取异常: {e}")
            # 数据获取失败不应该中断整个流程
            state["fetched_data"] = {
                "success": False,
                "message": f"数据服务异常: {str(e)}"
            }
            error_msg = f"\n[❌ 数据服务异常]: 暂时无法获取数据，将基于已有知识回答"
            state["messages"].append(SystemMessage(content=error_msg))
            return state

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
        """回测执行节点"""
        try:
            print("⚙️  执行回测...")
            state["current_step"] = "running_backtest"

            # 获取策略代码和数据
            strategy_code = state.get("strategy_code")

            # 从fetched_data中提取实际的K线数据
            fetched_data = state.get("fetched_data", {})
            data = None

            if isinstance(fetched_data, dict):
                # 优先检查直接在data字段中的数据
                if "data" in fetched_data:
                    raw_data = fetched_data["data"]
                    if isinstance(raw_data, list) and len(raw_data) > 0:
                        data = raw_data
                        print(f"✅ 从data字段提取到 {len(data)} 条K线")
                    elif isinstance(raw_data, dict):
                        print(f"⚠️ data字段是dict，需要进一步提取: {list(raw_data.keys())}")

                # 如果data字段没有，检查intermediate_steps
                if data is None and "intermediate_steps" in fetched_data:
                    for step in fetched_data["intermediate_steps"]:
                        if "observation" in step:
                            try:
                                import json
                                parsed = json.loads(step["observation"])
                                if isinstance(parsed, dict) and "data" in parsed:
                                    inner = parsed["data"]
                                    if isinstance(inner, list) and len(inner) > 0:
                                        data = inner
                                        print(f"✅ 从intermediate_steps提取到 {len(data)} 条K线")
                                        break
                            except:
                                pass

            print(f"📊 最终用于回测的数据: {len(data) if data else 0} 条")

            if not strategy_code:
                raise ValueError("缺少策略代码")

            if not data or (isinstance(data, list) and len(data) == 0):
                raise ValueError("缺少历史数据")

            # 调用BacktestAgent执行回测
            result = backtest_agent.run_backtest(
                strategy_code=strategy_code,
                data=data
            )

            if result["success"]:
                state["backtest_result"] = result["result"]
                state["backtest_summary"] = result["summary"]
                print(f"✅ 回测完成")
            else:
                state["error"] = result.get("error", "回测失败")

            return state

        except Exception as e:
            print(f"❌ 回测执行失败: {e}")
            state["error"] = f"回测执行异常: {str(e)}"
            return state

    async def _generate_response_node(self, state: AgentState) -> AgentState:
        """生成回复节点"""
        try:
            print("✨ 生成AI回复...")
            state["current_step"] = "generating_response"

            intent = state.get("analysis_result", "general_question")

            # 如果有回测结果，优先展示
            if intent == "backtest_request" and "backtest_summary" in state and state.get("backtest_result"):
                summary = state["backtest_summary"]

                # 简化：直接使用预格式化的摘要
                response_content = f"""
{summary}

💡 提示：
- 可以尝试调整策略参数（均线周期、止盈止损）
- 可以对比不同策略的表现
- 历史数据仅供参考，不构成投资建议
"""
                state["final_response"] = response_content
                print(f"💬 回测结果生成完成")
                return state

            # 如果是回测请求，已有策略代码，但还没有回测结果
            # 生成策略说明（包含数据摘要），但不回测
            if intent == "backtest_request" and state.get("strategy_code") and not state.get("backtest_result"):
                print("📝 策略代码已生成，等待用户确认回测")

                # 生成数据摘要
                data_summary = ""
                fetched_data = state.get("fetched_data", {})
                if fetched_data and fetched_data.get("success"):
                    data_list = fetched_data.get("data")
                    if data_list and isinstance(data_list, list) and len(data_list) > 0:
                        print(f"📊 检测到数据，准备格式化数据摘要...")

                        # 计算统计指标
                        import statistics as stats
                        closes = [item.get('close', 0) for item in data_list if item.get('close')]
                        highs = [item.get('high', 0) for item in data_list if item.get('high')]
                        lows = [item.get('low', 0) for item in data_list if item.get('low')]
                        pct_chgs = [item.get('pct_chg', 0) for item in data_list if item.get('pct_chg')]

                        max_price = max(highs) if highs else 0
                        min_price = min(lows) if lows else 0
                        avg_close = stats.mean(closes) if closes else 0
                        latest_close = closes[-1] if closes else 0
                        first_close = closes[0] if closes else 0
                        total_return = ((latest_close - first_close) / first_close * 100) if first_close > 0 else 0

                        data_summary = f"""
📊 **数据分析**
- 数据量: {len(data_list)}条交易日
- 价格区间: {min_price:.2f}元 - {max_price:.2f}元
- 当前价格: {latest_close:.2f}元
- 期间涨跌: {total_return:+.2f}%
"""
                        print(f"✅ 数据摘要生成完成")

                strategy_name = state.get("strategy_name", "策略")
                response_content = f"""## 📊 策略已生成完成

**策略名称**: {strategy_name}

{data_summary}我已为您生成了**双均线策略**代码，将在{len(data_list) if data_list else 0}条交易日数据上进行回测。

### 📋 策略说明

- **策略类型**: 基于双均线（短期MA和长期MA）的趋势跟踪策略
- **代码位置**: 显示在右侧策略面板
- **执行方式**: 点击右侧面板的"运行回测"按钮开始回测

### ⚠️ 注意事项

- 策略基于历史数据回测，不构成投资建议
- 实盘交易需谨慎，建议先进行充分测试
- 可根据实际情况调整策略参数（均线周期）

准备就绪后，请点击右侧的**"运行回测"**按钮开始回测分析。
"""
                state["final_response"] = response_content
                print(f"💬 策略说明生成完成")
                return state

            # 根据意图调整提示词
            intent = state.get("analysis_result", "general_question")

            # 检查是否有数据，如果有则格式化数据
            fetched_data = state.get("fetched_data", {})
            data_context = ""

            if fetched_data and fetched_data.get("success"):
                data_list = fetched_data.get("data")
                if data_list and isinstance(data_list, list) and len(data_list) > 0:
                    print(f"📊 检测到数据，准备格式化数据给LLM...")
                    print(f"📊 数据条数: {len(data_list)}条")

                    # 计算完整数据的统计指标
                    import statistics as stats

                    closes = [item.get('close', 0) for item in data_list if item.get('close')]
                    highs = [item.get('high', 0) for item in data_list if item.get('high')]
                    lows = [item.get('low', 0) for item in data_list if item.get('low')]
                    volumes = [item.get('vol', 0) for item in data_list if item.get('vol')]
                    pct_chgs = [item.get('pct_chg', 0) for item in data_list if item.get('pct_chg')]

                    # 价格统计
                    max_price = max(highs) if highs else 0
                    min_price = min(lows) if lows else 0
                    avg_close = stats.mean(closes) if closes else 0
                    latest_close = closes[-1] if closes else 0
                    first_close = closes[0] if closes else 0
                    total_return = ((latest_close - first_close) / first_close * 100) if first_close > 0 else 0

                    # 涨跌幅统计
                    max_gain = max(pct_chgs) if pct_chgs else 0
                    max_loss = min(pct_chgs) if pct_chgs else 0
                    up_days = len([x for x in pct_chgs if x > 0])
                    down_days = len([x for x in pct_chgs if x < 0])
                    win_rate = (up_days / len(pct_chgs) * 100) if pct_chgs else 0

                    # 成交量统计
                    avg_volume = stats.mean(volumes) if volumes else 0
                    max_volume = max(volumes) if volumes else 0

                    # 找出最大涨跌幅的日期
                    max_gain_idx = pct_chgs.index(max_gain) if pct_chgs else -1
                    max_loss_idx = pct_chgs.index(max_loss) if pct_chgs else -1

                    data_summary = f"""
【完整数据统计】
📊 数据量: {len(data_list)}条交易日数据
📅 时间范围: {data_list[0].get('trade_date', 'N/A')} 至 {data_list[-1].get('trade_date', 'N/A')}

【价格分析】
• 期间最高价: {max_price:.2f}元
• 期间最低价: {min_price:.2f}元
• 平均收盘价: {avg_close:.2f}元
• 期初价格: {first_close:.2f}元
• 期末价格: {latest_close:.2f}元
• 期间涨跌: {total_return:+.2f}%

【涨跌幅统计】
• 最大单日涨幅: {max_gain:.2f}% (日期: {data_list[max_gain_idx].get('trade_date', 'N/A') if max_gain_idx >= 0 else 'N/A'})
• 最大单日跌幅: {max_loss:.2f}% (日期: {data_list[max_loss_idx].get('trade_date', 'N/A') if max_loss_idx >= 0 else 'N/A'})
• 上涨天数: {up_days}天
• 下跌天数: {down_days}天
• 胜率(上涨占比): {win_rate:.1f}%

【成交量分析】
• 平均成交量: {avg_volume:.2f}手
• 最大成交量: {max_volume:.2f}手 (日期: {data_list[volumes.index(max_volume)].get('trade_date', 'N/A') if max_volume in volumes else 'N/A'})

【最近5个交易日详情】
"""
                    # 最近5天详细信息
                    recent_5 = data_list[-5:] if len(data_list) >= 5 else data_list
                    for i, item in enumerate(recent_5):
                        trade_date = item.get('trade_date', 'N/A')
                        open_price = item.get('open', 0)
                        high = item.get('high', 0)
                        low = item.get('low', 0)
                        close = item.get('close', 0)
                        volume = item.get('vol', 0)
                        pct_chg = item.get('pct_chg', 0)

                        data_summary += f"""
{len(data_list) - len(recent_5) + i + 1}. {trade_date}
   收盘: {close:.2f}元 ({pct_chg:+.2f}%) 成交量: {volume:.2f}手
   振幅: {high-low:.2f}元 (开{open_price:.2f} 高{high:.2f} 低{low:.2f})
"""

                    data_context = data_summary
                    print(f"✅ 数据统计摘要生成完成，长度: {len(data_context)}字符")

            if intent == "investment_analysis":
                system_prompt = f"""你是一个专业的投资分析师。请基于用户的问题和之前的对话历史提供专业的投资建议和分析。

重点关注：基本面分析、技术面分析、市场趋势、投资风险等方面。请根据对话历史保持上下文连贯性。

{data_context}

请基于上述数据，进行具体的量化分析，包括：
1. 具体的价格数据（开盘、收盘、最高、最低）
2. 涨跌幅变化趋势
3. 成交量变化
4. 基于真实数据的投资建议"""
            elif intent == "risk_analysis":
                system_prompt = f"""你是一个专业的风险管理专家。请重点分析投资风险，包括：
                市场风险、信用风险、流动性风险、操作风险等，并提供风险控制建议。请根据对话历史保持上下文连贯性。

{data_context}

请基于上述数据，分析具体的风险指标。"""
            elif intent == "data_analysis":
                system_prompt = f"""你是一个专业的数据分析专家。请专注于市场数据分析、技术指标分析和数据可视化建议。
                请根据对话历史保持上下文连贯性。

{data_context}

请基于上述数据，提供具体的数据分析结果。"""
            elif intent == "backtest_request":
                system_prompt = """你是一个量化策略专家。请专注于投资策略的设计、回测分析和优化建议。
                包括策略逻辑、历史表现、风险收益特征等。请根据对话历史保持上下文连贯性。"""
            else:
                system_prompt = f"""你是一个友好的AI助手，专注于金融投资领域。
                请根据用户问题和之前的对话历史提供有用的信息和建议，保持对话的连贯性。

{data_context}

请基于上述数据，回答用户的问题。"""

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
                # 显示最近几条消息的简要内容
                recent_messages = optimized_messages[-3:] if len(optimized_messages) > 3 else optimized_messages
                for i, msg in enumerate(recent_messages):
                    msg_type = "👤用户" if isinstance(msg, HumanMessage) else "🤖AI" if isinstance(msg, AIMessage) else "⚙️系统"
                    content = str(msg.content)[:50] + "..." if len(str(msg.content)) > 50 else str(msg.content)
                    print(f"  {msg_type}: {content}")
            
            # 使用优化后的消息列表
            messages = optimized_messages
            
            print(f"🚀 开始调用模型...")
            
            # 直接使用LangChain的ChatOpenAI调用
            response = await self.llm.ainvoke(messages)
            response_content = response.content

            state["final_response"] = response_content
            print(f"💬 生成回复完成，长度: {len(response_content)}字符")

            return state
            
        except Exception as e:
            print(f"❌ 回复生成失败: {e}")
            state["error"] = f"回复生成失败: {str(e)}"
            return state
    
    async def _format_output_node(self, state: AgentState) -> AgentState:
        """格式化输出节点"""
        try:
            print("📝 格式化输出...")
            state["current_step"] = "formatting_output"

            # 添加时间戳和元信息
            formatted_response = {
                "content": state["final_response"],
                "timestamp": datetime.now().isoformat(),
                "intent": state.get("analysis_result", "unknown"),
                "conversation_id": state.get("conversation_id", ""),
                "agent": "handler_agent"
            }

            # 如果有策略代码，添加到响应中
            if state.get("strategy_code"):
                formatted_response["strategy_code"] = state["strategy_code"]
                print(f"📝 响应中包含策略代码，长度: {len(state['strategy_code'])}字符")

            state["final_response"] = formatted_response

            # 将AI回复添加到messages中，使checkpoint能够保存完整的对话历史
            response_content = formatted_response["content"]
            if isinstance(response_content, dict):
                response_content = response_content.get("content", response_content)
            state["messages"].append(AIMessage(content=str(response_content)))

            print("✅ 输出格式化完成")

            return state

        except Exception as e:
            print(f"❌ 输出格式化失败: {e}")
            state["error"] = f"输出格式化失败: {str(e)}"
            return state
    
    
    async def process_message(self, 
                             user_input: str, 
                             conversation_id: str = "") -> Dict[str, Any]:
        """
        处理用户消息的主入口
        
        Args:
            user_input: 用户输入内容
            conversation_id: 对话ID
            
        Returns:
            处理结果
        """
        try:
            print(f"\n🚀 HandlerAgent开始处理消息 - 对话ID: {conversation_id}")
            print(f"🧠 使用对话记忆功能 - thread_id: {conversation_id}")
            
            # 配置thread_id用于对话记忆
            config = {
                "configurable": {
                    "thread_id": conversation_id,
                    "checkpoint_ns": "",
                }
            }
            
            # 初始化状态 - 添加新的用户消息到messages中
            initial_state: AgentState = {
                "messages": [HumanMessage(content=user_input)],  # 这里会与历史消息合并
                "user_input": user_input,
                "conversation_id": conversation_id,
                "current_step": "initialized",
                "analysis_result": None,
                "needs_data": None,
                "data_request": None,
                "fetched_data": None,
                # 回测相关
                "strategy_code": None,
                "strategy_name": None,
                "user_confirmed_backtest": None,  # 默认为None，等待用户确认
                "backtest_result": None,
                "backtest_summary": None,
                "final_response": None,
                "error": None
            }
            
            # 运行工作流，传入config以启用历史记忆
            result = await self.graph.ainvoke(initial_state, config=config)

            if result.get("error"):
                print(f"❌ 处理失败: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "response": result["final_response"]
                }
            else:
                print("✅ 消息处理完成")
                return {
                    "success": True,
                    "response": result["final_response"]
                }
                
        except Exception as e:
            error_msg = f"HandlerAgent处理异常: {str(e)}"
            print(f"❌ {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "response": {
                    "content": "系统暂时无法处理您的请求，请稍后重试。",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                    "agent": "handler_agent"
                }
            }

    async def continue_backtest(self, conversation_id: str) -> Dict[str, Any]:
        """
        继续执行回测（用户确认后调用）

        直接从checkpoint恢复state并执行回测，不重新走workflow

        Args:
            conversation_id: 对话ID

        Returns:
            处理结果
        """
        try:
            print(f"\n🔄 继续回测执行 - 对话ID: {conversation_id}")

            # 配置thread_id用于恢复对话状态
            config = {
                "configurable": {
                    "thread_id": conversation_id,
                    "checkpoint_ns": "",
                }
            }

            # 获取当前checkpoint的state
            current_state = await self.graph.aget_state(config)
            print(f"📥 从checkpoint恢复state，当前步骤: {current_state.values.get('current_step', 'unknown')}")

            # 检查是否有策略代码
            if not current_state.values.get("strategy_code"):
                error_msg = "未找到策略代码，无法执行回测"
                print(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

            # 直接执行回测节点（不经过workflow）
            print(f"🎯 直接执行回测节点...")

            # 创建包含必要信息的state
            backtest_state = AgentState(current_state.values)
            backtest_state["user_confirmed_backtest"] = True  # 设置确认标志

            # 依次执行：run_backtest → generate_response → format_output
            backtest_state = await self._run_backtest_node(backtest_state)

            if backtest_state.get("error"):
                print(f"❌ 回测执行失败: {backtest_state['error']}")
                return {
                    "success": False,
                    "error": backtest_state["error"],
                    "response": backtest_state.get("final_response")
                }

            backtest_state = await self._generate_response_node(backtest_state)
            backtest_state = await self._format_output_node(backtest_state)

            # 更新checkpoint
            await self.graph.aupdate_state(config, backtest_state)

            print("✅ 回测执行完成")

            # 返回完整结果
            return {
                "success": True,
                "response": backtest_state["final_response"],
                "backtest_result": backtest_state.get("backtest_result"),
                "backtest_summary": backtest_state.get("backtest_summary")
            }

        except Exception as e:
            error_msg = f"回测执行异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": error_msg,
                "response": {
                    "content": f"回测执行失败: {str(e)}",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                    "agent": "handler_agent"
                }
            }


# 全局HandlerAgent实例
handler_agent = HandlerAgent()
