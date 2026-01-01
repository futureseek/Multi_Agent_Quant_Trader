"""
HandlerAgent 核心实现
使用LangGraph框架构建的主控Agent
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict

from ..config.config_manager import config_manager
from .message_manager import MessageManager

class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[List, add_messages]
    user_input: str
    conversation_id: str
    current_step: str
    analysis_result: Optional[str]
    final_response: Optional[str]
    error: Optional[str]

class HandlerAgent:
    """主控Agent - 系统的大脑和指挥官"""
    
    def __init__(self):
        """初始化HandlerAgent"""
        # Agent名称
        self.name = "handler_agent"
        
        # 获取配置信息
        agent_config = config_manager.get_model_config(self.name)
        
        # 直接使用LangChain的ChatOpenAI
        self.llm = ChatOpenAI(
            model=agent_config["model_name"],
            api_key=agent_config["api_key"],
            base_url=agent_config["base_url"],
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
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("format_output", self._format_output_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # 定义流程
        workflow.add_edge(START, "parse_input")
        workflow.add_edge("parse_input", "analyze_intent")
        workflow.add_edge("analyze_intent", "generate_response")
        workflow.add_edge("generate_response", "format_output")
        workflow.add_edge("format_output", END)
        workflow.add_edge("handle_error", END)
        
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
    
    async def _handle_error_node(self, state: AgentState) -> AgentState:
        """错误处理节点"""
        error_msg = state.get("error", "未知错误")
        print(f"🚨 处理错误: {error_msg}")
        
        state["final_response"] = {
            "content": "抱歉，处理您的请求时出现了问题。请稍后重试或联系技术支持。",
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "conversation_id": state.get("conversation_id", ""),
            "agent": "handler_agent"
        }
        
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
