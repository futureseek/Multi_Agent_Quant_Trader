"""
API路由
负责处理前后端数据交互的API接口
"""

from flask import Blueprint, request, jsonify
import uuid
from datetime import datetime

api_bp = Blueprint('api', __name__)

# 临时存储（后续会替换为数据库）
conversations = {}
messages = {}

@api_bp.route('/conversations/create', methods=['POST'])
def create_conversation():
    """创建新对话"""
    try:
        data = request.get_json() or {}
        
        conversation_id = str(uuid.uuid4())
        title = data.get('title', f'新对话 {datetime.now().strftime("%m-%d %H:%M")}')
        
        conversations[conversation_id] = {
            'conversation_id': conversation_id,
            'title': title,
            'created_at': datetime.now().isoformat(),
            'message_count': 0,
            'last_message_time': None
        }
        
        return jsonify(conversations[conversation_id])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/conversations/list', methods=['GET'])
def list_conversations():
    """获取对话列表"""
    try:
        conversation_list = list(conversations.values())
        # 按创建时间倒序排列
        conversation_list.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'conversations': conversation_list})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/conversations/<conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    """获取指定对话的消息列表"""
    try:
        if conversation_id not in conversations:
            return jsonify({'error': '对话不存在'}), 404
        
        conversation_messages = [
            msg for msg in messages.values() 
            if msg['conversation_id'] == conversation_id
        ]
        
        # 按时间顺序排列
        conversation_messages.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': conversation_messages
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """删除对话"""
    try:
        if conversation_id not in conversations:
            return jsonify({'error': '对话不存在'}), 404
        
        # 删除对话
        del conversations[conversation_id]
        
        # 删除相关消息
        message_keys_to_delete = [
            key for key, msg in messages.items() 
            if msg['conversation_id'] == conversation_id
        ]
        for key in message_keys_to_delete:
            del messages[key]
        
        return jsonify({'success': True, 'message': '对话已删除'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/messages/send', methods=['POST'])
def send_message():
    """发送消息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        conversation_id = data.get('conversation_id')
        message_content = data.get('message')
        
        if not conversation_id or not message_content:
            return jsonify({'error': '缺少必要参数'}), 400
        
        if conversation_id not in conversations:
            return jsonify({'error': '对话不存在'}), 404
        
        # 创建用户消息
        user_message_id = str(uuid.uuid4())
        user_message = {
            'message_id': user_message_id,
            'conversation_id': conversation_id,
            'role': 'user',
            'content': message_content,
            'timestamp': datetime.now().isoformat()
        }
        
        messages[user_message_id] = user_message
        
        # 调用Service层处理消息
        try:
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from src.service_layer.api.service import sync_process_user_message
            
            # 调用Service层
            service_result = sync_process_user_message(
                user_input=message_content,
                conversation_id=conversation_id
            )
            
            if service_result["success"]:
                # 创建AI回复消息
                ai_message_id = str(uuid.uuid4())
                ai_response = service_result["response"]
                ai_message = {
                    'message_id': ai_message_id,
                    'conversation_id': conversation_id,
                    'role': 'assistant',
                    'content': ai_response["content"],
                    'timestamp': ai_response["timestamp"],
                    'agent': ai_response.get("agent", "handler_agent"),
                    'intent': ai_response.get("intent", "unknown")
                }
                
                messages[ai_message_id] = ai_message
                
                # 更新对话信息
                conversations[conversation_id]['message_count'] += 2  # 用户消息+AI回复
                conversations[conversation_id]['last_message_time'] = ai_message['timestamp']
                
                return jsonify({
                    'success': True,
                    'user_message_id': user_message_id,
                    'ai_message_id': ai_message_id,
                    'conversation_id': conversation_id,
                    'ai_response': ai_message,
                    'agents_used': service_result.get("agents_used", ["handler_agent"]),
                    'processing_status': service_result.get("status", "completed")
                })
            else:
                # Service层处理失败
                return jsonify({
                    'success': False,
                    'error': service_result.get("error", "Service层处理失败"),
                    'user_message_id': user_message_id,
                    'conversation_id': conversation_id
                })
                
        except Exception as service_error:
            # Service层调用异常，返回用户消息但标记处理失败
            print(f"❌ Service层调用失败: {service_error}")
            return jsonify({
                'success': False,
                'error': f"AI服务暂时不可用: {str(service_error)}",
                'user_message_id': user_message_id,
                'conversation_id': conversation_id
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/messages/<message_id>/status', methods=['GET'])
def get_message_status(message_id):
    """获取消息处理状态（模拟）"""
    try:
        if message_id not in messages:
            return jsonify({'error': '消息不存在'}), 404
        
        # 模拟处理状态
        return jsonify({
            'message_id': message_id,
            'status': 'completed',  # processing, completed, failed
            'current_agent': 'data_analyst',
            'progress': 100,
            'partial_response': '分析完成'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
