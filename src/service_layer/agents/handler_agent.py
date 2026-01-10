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
        """构建LangGraph工作流"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("parse_input", self._parse_input_node)
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("check_data_need", self._check_data_need_node)
        workflow.add_node("fetch_data", self._fetch_data_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("format_output", self._format_output_node)
        
        # 定义流程
        workflow.add_edge(START, "parse_input")
        workflow.add_edge("parse_input", "analyze_intent")
        workflow.add_edge("analyze_intent", "check_data_need")
        
        # 条件分支：根据是否需要数据决定路径
        workflow.add_conditional_edges(
            "check_data_need",
            self._should_fetch_data,
            {
                "fetch_data": "fetch_data",
                "generate_response": "generate_response"
            }
        )
        
        workflow.add_edge("fetch_data", "generate_response")
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
            
            if any(keyword in user_input for keyword in ["股票", "投资", "分析", "策略"]):
                intent = "investment_analysis"
            elif any(keyword in user_input for keyword in ["风险", "回撤", "波动"]):
                intent = "risk_analysis"
            elif any(keyword in user_input for keyword in ["回测", "策略", "收益"]):
                intent = "strategy_analysis"
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
            
            # 构建AI判断提示词
            judge_prompt = f"""
你是一个专业的投资分析助手。请判断用户的以下问题是否需要获取实时股票数据来进行回答。

用户问题："{state['user_input']}"

判断标准：
1. 如果问题涉及具体股票的价格、行情、K线数据、技术分析等，需要数据
2. 如果问题涉及某只股票的历史表现、走势分析等，需要数据  
3. 如果是一般性的投资理论、概念解释、策略讨论等，不需要数据
4. 如果是问候、介绍等日常对话，不需要数据

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
                state["fetched_data"] = data_result
                print(f"✅ 数据获取成功")
                
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
    
    async def _generate_response_node(self, state: AgentState) -> AgentState:
        """生成回复节点"""
        try:
            print("✨ 生成AI回复...")
            state["current_step"] = "generating_response"
            
            # 根据意图调整提示词
            intent = state.get("analysis_result", "general_question")
            
            if intent == "investment_analysis":
                system_prompt = """你是一个专业的投资分析师。请基于用户的问题和之前的对话历史提供专业的投资建议和分析。
                重点关注：基本面分析、技术面分析、市场趋势、投资风险等方面。请根据对话历史保持上下文连贯性。"""
            elif intent == "risk_analysis":
                system_prompt = """你是一个专业的风险管理专家。请重点分析投资风险，包括：
                市场风险、信用风险、流动性风险、操作风险等，并提供风险控制建议。请根据对话历史保持上下文连贯性。"""
            elif intent == "strategy_analysis":
                system_prompt = """你是一个量化策略专家。请专注于投资策略的设计、回测分析和优化建议。
                包括策略逻辑、历史表现、风险收益特征等。请根据对话历史保持上下文连贯性。"""
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
            print(f"💬 生成回复完成，长度: {len(response_content)}")
            
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
            
            state["final_response"] = formatted_response
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
                "final_response": None,
                "error": None
            }
            
            # 运行工作流，传入config以启用历史记忆
            result = await self.graph.ainvoke(initial_state, config=config)
            
            # 添加AI回复到历史记忆中
            if result.get("final_response") and not result.get("error"):
                ai_response_content = result["final_response"]["content"] if isinstance(result["final_response"], dict) else result["final_response"]
                # 手动添加AI回复到对话历史中
                ai_message_state = {
                    "messages": [AIMessage(content=ai_response_content)],
                }
                # 使用相同的config保存AI回复
                await self.graph.ainvoke(ai_message_state, config=config)
            
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
    
    async def test_workflow(self) -> bool:
        """测试工作流是否正常"""
        try:
            test_result = await self.process_message(
                user_input="你好，请做一个简单的自我介绍。",
                conversation_id="test_conversation"
            )
            
            if test_result["success"]:
                print("✅ HandlerAgent工作流测试成功")
                return True
            else:
                print(f"❌ HandlerAgent工作流测试失败: {test_result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ HandlerAgent工作流测试异常: {e}")
            return False

# 全局HandlerAgent实例
handler_agent = HandlerAgent()
