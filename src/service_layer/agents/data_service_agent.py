"""
DataServiceAgent - 数据服务智能体
负责处理所有金融数据获取请求，提供高效的数据服务
使用LangChain 0.2版本的现代化实现
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from ..config.config_manager import config_manager
from ..tools.daily_data_tool import get_daily_stock_data
from .message_manager import MessageManager


class DataServiceAgent:
    """数据服务智能体 - 专门负责金融数据获取和处理"""
    
    def __init__(self):
        """初始化DataServiceAgent"""
        # Agent名称
        self.name = "data_service_agent"
        
        # 获取配置信息
        agent_config = config_manager.get_model_config(self.name)
        
        # 初始化LLM - 使用明确的参数名称避免proxies问题
        self.llm = ChatOpenAI(
            model=agent_config["model_name"],
            openai_api_key=agent_config["api_key"], 
            openai_api_base=agent_config["base_url"],
            temperature=0.1,  # 数据服务需要更准确，温度设低一点
            max_tokens=2000
        )
        
        # 获取系统提示词
        self.system_prompt = config_manager.get_prompt_config(self.name)
        
        # 初始化消息管理器
        self.message_manager = MessageManager(
            max_messages=50,   # 数据服务对话相对简单，减少消息数
            max_tokens=8000    # 减少token使用量
        )
        
        # 初始化工具列表
        self.tools = [get_daily_stock_data]
        
        # 创建提示词模板
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # 创建工具调用Agent
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt_template
        )
        
        # 创建Agent执行器 - 使用0.2版本的配置
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,  # 限制迭代次数，避免无限循环
            return_intermediate_steps=True  # 返回中间步骤，便于调试
        )
        
        # 会话缓存
        self.session_cache = {}
        
        print(f"✅ DataServiceAgent 初始化完成 - 模型: {agent_config['model_name']}")
        print(f"📊 可用数据工具: {[tool.name for tool in self.tools]}")
    
    async def process_data_request(self, 
                                  request: str,
                                  conversation_id: str = "",
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理数据请求的主入口
        
        Args:
            request: 数据请求描述
            conversation_id: 对话ID
            context: 上下文信息
            
        Returns:
            处理结果
        """
        try:
            print(f"\n🔍 DataServiceAgent开始处理数据请求")
            print(f"📋 请求内容: {request[:100]}...")
            
            # 检查缓存
            cache_key = f"{conversation_id}:{hash(request)}"
            if cache_key in self.session_cache:
                print(f"💾 命中缓存，直接返回结果")
                return self.session_cache[cache_key]
            
            # 使用新版本的invoke方法
            print(f"🤖 调用DataServiceAgent执行数据获取...")
            result = await self.executor.ainvoke({
                "input": request
            })
            
            # 处理结果 - 适配0.2版本的返回格式
            if result and "output" in result:
                response_data = {
                    "success": True,
                    "message": "数据获取成功",
                    "content": result["output"],
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name,
                    "tools_used": [tool.name for tool in self.tools],
                    "context": context or {},
                    "intermediate_steps": result.get("intermediate_steps", [])
                }
                
                # 缓存结果
                self.session_cache[cache_key] = response_data
                
                print(f"✅ 数据请求处理完成")
                return response_data
            else:
                error_msg = "Agent执行未返回有效结果"
                print(f"❌ {error_msg}")
                return self._create_error_response(error_msg, "无法获取数据，请检查请求格式或重试")
                
        except Exception as e:
            error_msg = f"DataServiceAgent处理异常: {str(e)}"
            print(f"❌ {error_msg}")
            
            return self._create_error_response(error_msg, f"数据服务暂时不可用: {str(e)}")
    
    def _create_error_response(self, error_msg: str, user_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "message": error_msg,
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
            "agent": self.name
        }
    
    async def think_and_respond(self, 
                               handler_instruction: str,
                               conversation_id: str = "") -> Dict[str, Any]:
        """
        接收HandlerAgent的指令，思考并选择合适的数据工具返回结果
        
        Args:
            handler_instruction: HandlerAgent发来的指令
            conversation_id: 对话ID
            
        Returns:
            思考和处理结果
        """
        try:
            print(f"🧠 DataServiceAgent开始思考HandlerAgent的指令...")
            print(f"📨 收到指令: {handler_instruction[:100]}...")
            
            # 构建思考提示词
            thinking_prompt = f"""
作为专业的数据服务智能体，我收到了HandlerAgent的以下指令：
"{handler_instruction}"

我需要：
1. 理解指令的具体需求
2. 判断需要什么类型的数据
3. 选择合适的数据获取工具
4. 执行数据获取并返回结构化结果

请帮我分析这个指令并获取相应的数据。
"""
            
            # 调用数据处理逻辑
            result = await self.process_data_request(
                request=thinking_prompt,
                conversation_id=conversation_id,
                context={"source": "handler_agent", "instruction": handler_instruction}
            )
            
            # 为HandlerAgent添加思考过程信息
            if result["success"]:
                result["thinking_process"] = {
                    "received_instruction": handler_instruction,
                    "analysis": "已理解指令并成功获取数据",
                    "selected_tools": [tool.name for tool in self.tools],
                    "processing_time": datetime.now().isoformat()
                }
            
            return result
            
        except Exception as e:
            error_msg = f"DataServiceAgent思考处理异常: {str(e)}"
            print(f"❌ {error_msg}")
            return self._create_error_response(error_msg, f"思考处理失败: {str(e)}")
    
    def clear_cache(self, conversation_id: str = None):
        """
        清理缓存
        
        Args:
            conversation_id: 指定对话ID，如果为None则清理所有缓存
        """
        if conversation_id:
            # 清理指定对话的缓存
            keys_to_remove = [key for key in self.session_cache.keys() 
                            if key.startswith(f"{conversation_id}:")]
            for key in keys_to_remove:
                del self.session_cache[key]
            print(f"🗑️  清理了对话 {conversation_id} 的缓存，共 {len(keys_to_remove)} 条")
        else:
            # 清理所有缓存
            cache_count = len(self.session_cache)
            self.session_cache.clear()
            print(f"🗑️  清理了所有缓存，共 {cache_count} 条")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_count": len(self.session_cache),
            "tools_available": len(self.tools),
            "tool_names": [tool.name for tool in self.tools],
            "agent_name": self.name,
            "langchain_version": "0.2.x"
        }
    
    async def test_functionality(self) -> bool:
        """测试Agent功能是否正常"""
        try:
            print(f"🧪 开始测试DataServiceAgent功能...")
            
            # 测试数据请求
            test_request = "请获取平安银行(000001.SZ)最近5天的日K线数据"
            result = await self.process_data_request(
                request=test_request,
                conversation_id="test_conversation"
            )
            
            if result["success"]:
                print(f"✅ DataServiceAgent功能测试成功")
                print(f"📊 返回内容长度: {len(result['content'])}")
                return True
            else:
                print(f"❌ DataServiceAgent功能测试失败: {result['message']}")
                return False
                
        except Exception as e:
            print(f"❌ DataServiceAgent功能测试异常: {e}")
            return False
    
    async def test_thinking_capability(self) -> bool:
        """测试思考能力"""
        try:
            print(f"🧠 开始测试DataServiceAgent思考能力...")
            
            # 测试接收HandlerAgent指令的能力
            test_instruction = "用户想了解万科A股票的最近表现，请获取相关数据"
            result = await self.think_and_respond(
                handler_instruction=test_instruction,
                conversation_id="test_thinking"
            )
            
            if result["success"]:
                print(f"✅ DataServiceAgent思考能力测试成功")
                print(f"🤔 思考过程: {result.get('thinking_process', {}).get('analysis', 'N/A')}")
                return True
            else:
                print(f"❌ DataServiceAgent思考能力测试失败: {result['message']}")
                return False
                
        except Exception as e:
            print(f"❌ DataServiceAgent思考能力测试异常: {e}")
            return False


# 全局DataServiceAgent实例
data_service_agent = DataServiceAgent()
