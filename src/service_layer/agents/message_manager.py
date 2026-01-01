"""
MessageManager - 对话上下文管理器
负责智能管理Agent的对话历史，控制消息增长
"""

import tiktoken
from typing import List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from datetime import datetime


class MessageManager:
    """智能消息管理器 - 控制对话上下文增长"""
    
    def __init__(self, max_messages: int = 500, max_tokens: int = 50000):
        """
        初始化MessageManager
        
        Args:
            max_messages: 最大消息数量
            max_tokens: 最大token数量
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        
        # 使用默认的通用编码器
        self.encoding = tiktoken.get_encoding("cl100k_base")
            
        print(f"✅ MessageManager初始化完成 - 最大消息数: {max_messages}, 最大tokens: {max_tokens}")
    
    def count_tokens(self, message: BaseMessage) -> int:
        """计算单个消息的token数量"""
        try:
            content = str(message.content)
            return len(self.encoding.encode(content))
        except Exception as e:
            # 如果计算失败，使用近似估算 (1 token ≈ 4 characters)
            return len(str(message.content)) // 4
    
    def count_total_tokens(self, messages: List[BaseMessage]) -> int:
        """计算消息列表的总token数"""
        total = 0
        for msg in messages:
            total += self.count_tokens(msg)
        return total
    
    def get_message_priority(self, message: BaseMessage, index: int, total_count: int) -> int:
        """
        计算消息重要性评分 (分数越高越重要)
        
        Args:
            message: 消息对象
            index: 消息在列表中的位置
            total_count: 消息总数
            
        Returns:
            重要性评分 (0-100)
        """
        priority = 0
        
        # 1. 消息类型优先级
        if isinstance(message, SystemMessage):
            priority += 90  # 系统消息最重要
        elif isinstance(message, AIMessage):
            priority += 30  # AI回复次重要
        elif isinstance(message, HumanMessage):
            priority += 20  # 用户消息基础重要
        
        # 2. 位置优先级 (越新越重要)
        position_score = (index / total_count) * 30  # 0-30分
        priority += position_score
        
        # 3. 内容长度优先级 (较长的消息通常包含更多信息)
        content_length = len(str(message.content))
        if content_length > 200:
            priority += 10
        elif content_length > 100:
            priority += 5
        
        # 4. 关键词检测
        content_lower = str(message.content).lower()
        keywords = ['投资', '策略', '分析', '风险', '回测', '收益', '股票', '基金']
        keyword_count = sum(1 for kw in keywords if kw in content_lower)
        priority += keyword_count * 3
        
        return min(priority, 100)  # 限制最大值为100
    
    def compress_old_messages(self, messages: List[BaseMessage], keep_count: int) -> List[BaseMessage]:
        """
        压缩较旧的消息
        
        Args:
            messages: 原始消息列表
            keep_count: 保留的消息数量
            
        Returns:
            压缩后的消息列表
        """
        if len(messages) <= keep_count:
            return messages
        
        # 保留最近的消息
        recent_messages = messages[-keep_count:]
        old_messages = messages[:-keep_count]
        
        # 为旧消息生成摘要
        if old_messages:
            summary_content = self._generate_summary(old_messages)
            summary_message = SystemMessage(content=f"[历史对话摘要] {summary_content}")
            
            # 确保第一个消息是SystemMessage
            if recent_messages and isinstance(recent_messages[0], SystemMessage):
                return [recent_messages[0], summary_message] + recent_messages[1:]
            else:
                return [summary_message] + recent_messages
        
        return recent_messages
    
    def _generate_summary(self, messages: List[BaseMessage]) -> str:
        """生成消息摘要"""
        if not messages:
            return "无历史对话"
        
        # 统计消息类型
        user_msgs = [msg for msg in messages if isinstance(msg, HumanMessage)]
        ai_msgs = [msg for msg in messages if isinstance(msg, AIMessage)]
        
        # 提取关键主题
        all_content = " ".join([str(msg.content) for msg in messages])
        keywords = ['投资', '策略', '分析', '风险', '股票', '基金', '回测']
        mentioned_topics = [kw for kw in keywords if kw in all_content]
        
        # 生成摘要
        summary_parts = []
        summary_parts.append(f"包含{len(user_msgs)}个用户问题和{len(ai_msgs)}个AI回复")
        
        if mentioned_topics:
            summary_parts.append(f"主要讨论了：{', '.join(mentioned_topics[:3])}")
        
        # 获取最后几个关键对话
        important_exchanges = []
        for i in range(len(messages) - 1):
            if isinstance(messages[i], HumanMessage) and i + 1 < len(messages):
                user_q = str(messages[i].content)[:50] + "..."
                if len(important_exchanges) < 2:  # 只保留最后2个重要对话
                    important_exchanges.append(user_q)
        
        if important_exchanges:
            summary_parts.append(f"最近讨论：{'; '.join(important_exchanges)}")
        
        return " | ".join(summary_parts)
    
    def optimize_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        优化消息列表，控制增长
        
        Args:
            messages: 原始消息列表
            
        Returns:
            优化后的消息列表
        """
        if not messages:
            return messages
        
        print(f"📊 消息优化前: {len(messages)}条消息, {self.count_total_tokens(messages)}个tokens")
        
        # 1. 首先检查数量限制
        if len(messages) > self.max_messages:
            print(f"⚠️  消息数量超限({len(messages)} > {self.max_messages})，应用数量压缩")
            messages = self.compress_old_messages(messages, self.max_messages)
        
        # 2. 检查token限制
        total_tokens = self.count_total_tokens(messages)
        if total_tokens > self.max_tokens:
            print(f"⚠️  Token数量超限({total_tokens} > {self.max_tokens})，应用token压缩")
            messages = self._compress_by_tokens(messages)
        
        print(f"📊 消息优化后: {len(messages)}条消息, {self.count_total_tokens(messages)}个tokens")
        return messages
    
    def _compress_by_tokens(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """根据token限制压缩消息"""
        if not messages:
            return messages
        
        # 保护SystemMessage
        system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
        other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
        
        # 为每个消息计算优先级
        message_priorities = []
        for i, msg in enumerate(other_messages):
            priority = self.get_message_priority(msg, i, len(other_messages))
            tokens = self.count_tokens(msg)
            message_priorities.append((msg, priority, tokens, i))
        
        # 按优先级排序 (高优先级在前)
        message_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # 选择消息直到达到token限制
        selected_messages = system_messages[:]
        current_tokens = sum(self.count_tokens(msg) for msg in system_messages)
        
        for msg, priority, tokens, original_index in message_priorities:
            if current_tokens + tokens <= self.max_tokens:
                selected_messages.append(msg)
                current_tokens += tokens
            else:
                break
        
        # 如果删除了太多消息，至少保留最近的几条
        if len(selected_messages) < 6:  # 至少保留6条消息
            recent_messages = messages[-6:]
            return self.compress_old_messages(recent_messages, 6)
        
        return selected_messages
    
    def add_message(self, messages: List[BaseMessage], new_message: BaseMessage) -> List[BaseMessage]:
        """
        添加新消息并优化列表
        
        Args:
            messages: 当前消息列表
            new_message: 要添加的新消息
            
        Returns:
            优化后的消息列表
        """
        updated_messages = messages + [new_message]
        return self.optimize_messages(updated_messages)
    
    def get_stats(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """获取消息统计信息"""
        if not messages:
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "system_messages": 0,
                "user_messages": 0,
                "ai_messages": 0
            }
        
        stats = {
            "total_messages": len(messages),
            "total_tokens": self.count_total_tokens(messages),
            "system_messages": sum(1 for msg in messages if isinstance(msg, SystemMessage)),
            "user_messages": sum(1 for msg in messages if isinstance(msg, HumanMessage)),
            "ai_messages": sum(1 for msg in messages if isinstance(msg, AIMessage)),
            "avg_tokens_per_message": self.count_total_tokens(messages) // len(messages)
        }
        
        return stats
