"""
HandlerAgent 核心实现
使用LangGraph框架构建的主控Agent
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict

from ..config.config_manager import config_manager

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
        # 获取配置信息
        agent_config = config_manager.get_model_config("handler_agent")
        
        # 直接使用LangChain的ChatOpenAI
        self.llm = ChatOpenAI(
            model=agent_config["model_name"],
            api_key=agent_config["api_key"],
            base_url=agent_config["base_url"],
            temperature=0.7
        )
        
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
        
        return workflow.compile()
    
    async def _parse_input_node(self, state: AgentState) -> AgentState:
        """解析输入节点"""
        try:
            print(f"📥 解析用户输入: {state['user_input'][:50]}...")
            
            # 更新状态
            state["current_step"] = "parsing_input"
            state["messages"] = [
                SystemMessage(content="""你是一个专业的量化投资AI助手。
                你的任务是帮助用户进行投资分析、策略制定和风险评估。
                请以专业、友好的态度回应用户的问题。"""),
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
                system_prompt = """你是一个专业的投资分析师。请基于用户的问题提供专业的投资建议和分析。
                重点关注：基本面分析、技术面分析、市场趋势、投资风险等方面。"""
            elif intent == "risk_analysis":
                system_prompt = """你是一个专业的风险管理专家。请重点分析投资风险，包括：
                市场风险、信用风险、流动性风险、操作风险等，并提供风险控制建议。"""
            elif intent == "strategy_analysis":
                system_prompt = """你是一个量化策略专家。请专注于投资策略的设计、回测分析和优化建议。
                包括策略逻辑、历史表现、风险收益特征等。"""
            else:
                system_prompt = """你是一个友好的AI助手，专注于金融投资领域。
                请根据用户问题提供有用的信息和建议。"""
            
            # 构建消息列表
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=state["user_input"])
            ]
            
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
            
            # 初始化状态
            initial_state: AgentState = {
                "messages": [],
                "user_input": user_input,
                "conversation_id": conversation_id,
                "current_step": "initialized",
                "analysis_result": None,
                "final_response": None,
                "error": None
            }
            
            # 运行工作流
            result = await self.graph.ainvoke(initial_state)
            
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
