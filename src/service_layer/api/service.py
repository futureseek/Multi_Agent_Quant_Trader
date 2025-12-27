"""
Service层API接口
提供给Web层调用的标准化服务接口
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
from ..agents.handler_agent import handler_agent

class ServiceAPI:
    """Service层统一API接口"""
    
    def __init__(self):
        """初始化Service API"""
        self.handler_agent = handler_agent
        print("✅ ServiceAPI 初始化完成")
    
    async def process_user_message(self, 
                                 user_input: str, 
                                 conversation_id: str,
                                 user_id: str = None) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            user_input: 用户输入内容
            conversation_id: 对话ID
            user_id: 用户ID（可选）
            
        Returns:
            处理结果
        """
        try:
            print(f"\n🔄 ServiceAPI收到消息处理请求")
            print(f"📝 用户输入: {user_input[:100]}...")
            print(f"🗨️ 对话ID: {conversation_id}")
            
            # 调用HandlerAgent处理消息
            result = await self.handler_agent.process_message(
                user_input=user_input,
                conversation_id=conversation_id
            )
            
            # 格式化返回结果
            if result["success"]:
                return {
                    "success": True,
                    "message_id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{conversation_id}",
                    "response": result["response"],
                    "processing_time": None,  # 可以添加处理时间统计
                    "agents_used": ["handler_agent"],
                    "status": "completed"
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "response": result["response"],
                    "status": "failed"
                }
                
        except Exception as e:
            error_msg = f"ServiceAPI处理异常: {str(e)}"
            print(f"❌ {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "response": {
                    "content": "系统处理异常，请稍后重试。",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                    "agent": "service_api"
                },
                "status": "error"
            }
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        获取所有Agent的状态
        
        Returns:
            Agent状态信息
        """
        try:
            # 这里可以添加更多Agent的状态检查
            return {
                "agents": {
                    "handler_agent": {
                        "status": "active",
                        "model": self.handler_agent.llm.model_name,
                        "last_activity": datetime.now().isoformat()
                    }
                },
                "system_status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "agents": {},
                "system_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_system(self) -> Dict[str, Any]:
        """
        系统自测试
        
        Returns:
            测试结果
        """
        try:
            print("🧪 开始系统自测试...")
            
            # 测试HandlerAgent工作流
            handler_test = await self.handler_agent.test_workflow()
            
            return {
                "success": handler_test,
                "tests": {
                    "handler_agent_workflow": handler_test,
                },
                "system_status": "healthy" if handler_test else "degraded",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "system_status": "error",
                "timestamp": datetime.now().isoformat()
            }

# 全局ServiceAPI实例
service_api = ServiceAPI()

# 同步包装器函数
def sync_process_user_message(user_input: str, conversation_id: str, user_id: str = None) -> Dict[str, Any]:
    """
    同步处理用户消息（供Web层调用）
    """
    return asyncio.run(service_api.process_user_message(user_input, conversation_id, user_id))

def sync_get_agent_status() -> Dict[str, Any]:
    """
    同步获取Agent状态
    """
    return asyncio.run(service_api.get_agent_status())

def sync_test_system() -> Dict[str, Any]:
    """
    同步系统测试
    """
    return asyncio.run(service_api.test_system())
