/**
 * Multi-Agent Quant Trader 主JavaScript文件
 * 负责前端交互逻辑和API通信
 */

// 全局变量
let currentConversationId = null;
let socket = null;

// DOM元素引用
const elements = {
    newConversationBtn: null,
    conversationList: null,
    messageInput: null,
    sendBtn: null,
    chatHistory: null,
    agentStatusItems: null,
    resultsPanel: null
};

// 应用程序类
class QuantTraderApp {
    constructor() {
        this.init();
    }

    // 初始化应用
    init() {
        this.initElements();
        this.initEventListeners();
        this.initSocket();
        this.loadConversations();
    }

    // 初始化DOM元素引用
    initElements() {
        elements.newConversationBtn = document.getElementById('new-conversation');
        elements.conversationList = document.getElementById('conversation-list');
        elements.messageInput = document.getElementById('message-input');
        elements.sendBtn = document.getElementById('send-btn');
        elements.chatHistory = document.getElementById('chat-history');
        elements.agentStatusItems = document.querySelectorAll('.agent-status-item');
        elements.resultsPanel = document.getElementById('results-panel');
    }

    // 初始化事件监听器
    initEventListeners() {
        // 新建对话按钮
        elements.newConversationBtn?.addEventListener('click', () => {
            this.createNewConversation();
        });

        // 发送消息按钮
        elements.sendBtn?.addEventListener('click', () => {
            this.sendMessage();
        });

        // 输入框回车发送
        elements.messageInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 建议卡片点击
        document.addEventListener('click', (e) => {
            if (e.target.closest('.suggestion-card')) {
                const suggestion = e.target.closest('.suggestion-card').dataset.suggestion;
                if (suggestion) {
                    elements.messageInput.value = suggestion;
                    this.sendMessage();
                }
            }
        });
    }

    // 初始化WebSocket连接
    initSocket() {
        try {
            socket = io();
            
            socket.on('connect', () => {
                console.log('WebSocket连接成功');
                this.updateConnectionStatus(true);
            });

            socket.on('disconnect', () => {
                console.log('WebSocket连接断开');
                this.updateConnectionStatus(false);
            });

            socket.on('agent_status_update', (data) => {
                this.updateAgentStatus(data);
            });

            socket.on('message_response', (data) => {
                this.displayMessage(data);
            });

        } catch (error) {
            console.error('WebSocket初始化失败:', error);
        }
    }

    // 更新连接状态
    updateConnectionStatus(isConnected) {
        const statusElement = document.querySelector('.navbar-text');
        if (statusElement) {
            const icon = statusElement.querySelector('i');
            if (isConnected) {
                icon.className = 'fas fa-circle text-success me-1';
                statusElement.innerHTML = '<i class="fas fa-circle text-success me-1"></i>已连接';
            } else {
                icon.className = 'fas fa-circle text-danger me-1';
                statusElement.innerHTML = '<i class="fas fa-circle text-danger me-1"></i>连接断开';
            }
        }
    }

    // 加载对话列表
    async loadConversations() {
        try {
            const response = await fetch('/api/conversations/list');
            const data = await response.json();
            
            if (data.conversations) {
                this.renderConversationList(data.conversations);
                
                // 如果有对话，启用输入框
                if (data.conversations.length > 0) {
                    this.enableInput();
                }
            }
        } catch (error) {
            console.error('加载对话列表失败:', error);
            this.showError('加载对话列表失败');
        }
    }

    // 渲染对话列表
    renderConversationList(conversations) {
        if (!elements.conversationList) return;

        if (conversations.length === 0) {
            elements.conversationList.innerHTML = `
                <div class="conversation-placeholder text-center text-muted py-4">
                    <i class="fas fa-comments fa-2x mb-2"></i>
                    <p>点击上方按钮开始新对话</p>
                </div>
            `;
            return;
        }

        const listHTML = conversations.map(conv => `
            <div class="conversation-item" data-conversation-id="${conv.conversation_id}">
                <div class="conversation-title">${conv.title}</div>
                <div class="conversation-meta">
                    <span class="message-count">${conv.message_count}条消息</span>
                    <button class="btn-delete" onclick="app.deleteConversation('${conv.conversation_id}', event)">×</button>
                </div>
            </div>
        `).join('');

        elements.conversationList.innerHTML = listHTML;

        // 添加点击事件
        elements.conversationList.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('btn-delete')) {
                    const conversationId = item.dataset.conversationId;
                    this.loadConversation(conversationId);
                }
            });
        });
    }

    // 创建新对话
    async createNewConversation() {
        try {
            const response = await fetch('/api/conversations/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            const data = await response.json();
            
            if (data.conversation_id) {
                await this.loadConversations();
                this.loadConversation(data.conversation_id);
                this.enableInput();
            }
        } catch (error) {
            console.error('创建对话失败:', error);
            this.showError('创建对话失败');
        }
    }

    // 删除对话
    async deleteConversation(conversationId, event) {
        event?.stopPropagation();
        
        if (!confirm('确定要删除这个对话吗？')) return;

        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadConversations();
                
                // 如果删除的是当前对话，清空聊天区域
                if (currentConversationId === conversationId) {
                    this.clearChatHistory();
                    currentConversationId = null;
                }
            }
        } catch (error) {
            console.error('删除对话失败:', error);
            this.showError('删除对话失败');
        }
    }

    // 加载对话
    async loadConversation(conversationId) {
        try {
            currentConversationId = conversationId;
            
            // 更新活动状态
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelector(`[data-conversation-id="${conversationId}"]`)?.classList.add('active');

            // 加载消息
            const response = await fetch(`/api/conversations/${conversationId}/messages`);
            const data = await response.json();
            
            this.clearChatHistory();
            
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(message => {
                    this.displayMessage(message, false);
                });
            }
            
            this.enableInput();
            
        } catch (error) {
            console.error('加载对话失败:', error);
            this.showError('加载对话失败');
        }
    }

    // 发送消息
    async sendMessage() {
        const message = elements.messageInput?.value?.trim();
        if (!message || !currentConversationId) return;

        try {
            // 立即显示用户消息
            this.displayMessage({
                role: 'user',
                content: message,
                timestamp: new Date().toISOString()
            });

            // 清空输入框
            elements.messageInput.value = '';

            // 发送到服务器
            const response = await fetch('/api/messages/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_id: currentConversationId,
                    message: message
                })
            });

            const data = await response.json();
            
            if (data.success && data.ai_response) {
                // 显示真实的AI回复
                this.displayMessage({
                    role: 'assistant',
                    content: data.ai_response.content,
                    timestamp: data.ai_response.timestamp,
                    agent: data.ai_response.agent,
                    intent: data.ai_response.intent
                });
            } else if (data.error) {
                // 显示错误信息
                this.showError(data.error);
                this.displayMessage({
                    role: 'assistant',
                    content: '抱歉，处理您的消息时遇到了问题：' + data.error,
                    timestamp: new Date().toISOString(),
                    is_error: true
                });
            }

        } catch (error) {
            console.error('发送消息失败:', error);
            this.showError('发送消息失败');
        }
    }

    // 显示消息
    displayMessage(message, animate = true) {
        if (!elements.chatHistory) return;

        // 如果是第一条消息，清除欢迎信息
        const welcomeMessage = elements.chatHistory.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        const messageElement = document.createElement('div');
        const isUser = message.role === 'user';
        const isError = message.is_error === true;
        
        // 设置消息样式类
        let messageClasses = `message ${message.role}`;
        if (animate) messageClasses += ' fade-in';
        if (isError) messageClasses += ' error';
        
        messageElement.className = messageClasses;

        const avatarIcon = isUser ? 'fas fa-user' : (isError ? 'fas fa-exclamation-triangle' : 'fas fa-robot');
        const avatarClass = isUser ? 'user' : 'assistant';

        // 为AI消息添加Agent标识和意图标签
        let agentBadge = '';
        if (!isUser && message.agent) {
            const agentName = message.agent === 'handler_agent' ? '智能助手' : message.agent;
            const intentName = this.getIntentDisplayName(message.intent);
            agentBadge = `
                <div class="message-meta">
                    <span class="agent-badge">${agentName}</span>
                    ${intentName ? `<span class="intent-badge">${intentName}</span>` : ''}
                </div>
            `;
        }

        messageElement.innerHTML = `
            ${!isUser ? `<div class="message-avatar ${avatarClass} ${isError ? 'error' : ''}">
                <i class="${avatarIcon}"></i>
            </div>` : ''}
            <div class="message-content">
                ${agentBadge}
                <div class="message-text ${isError ? 'error-text' : ''}">${message.content}</div>
                <div class="message-time">${this.formatTime(message.timestamp)}</div>
            </div>
            ${isUser ? `<div class="message-avatar ${avatarClass}">
                <i class="${avatarIcon}"></i>
            </div>` : ''}
        `;

        elements.chatHistory.appendChild(messageElement);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;

        // 如果是AI消息，添加打字机效果
        if (!isUser && animate && !isError) {
            this.addTypingEffect(messageElement);
        }
    }

    // 获取意图显示名称
    getIntentDisplayName(intent) {
        const intentMap = {
            'investment_analysis': '投资分析',
            'risk_analysis': '风险分析', 
            'strategy_analysis': '策略分析',
            'general_question': '通用问答'
        };
        return intentMap[intent] || null;
    }

    // 添加打字机效果
    addTypingEffect(messageElement) {
        const messageText = messageElement.querySelector('.message-text');
        if (!messageText) return;

        messageText.style.opacity = '0.8';
        setTimeout(() => {
            messageText.style.opacity = '1';
        }, 300);
    }

    // 格式化时间
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    // 清空聊天历史
    clearChatHistory() {
        if (elements.chatHistory) {
            elements.chatHistory.innerHTML = '';
        }
    }

    // 启用输入
    enableInput() {
        if (elements.messageInput) {
            elements.messageInput.disabled = false;
            elements.messageInput.placeholder = '请输入您的问题...';
        }
        if (elements.sendBtn) {
            elements.sendBtn.disabled = false;
        }
    }

    // 禁用输入
    disableInput() {
        if (elements.messageInput) {
            elements.messageInput.disabled = true;
            elements.messageInput.placeholder = '请先创建或选择一个对话...';
        }
        if (elements.sendBtn) {
            elements.sendBtn.disabled = true;
        }
    }

    // 更新Agent状态
    updateAgentStatus(data) {
        const agentElement = document.querySelector(`[data-agent="${data.agent_id}"]`);
        if (agentElement) {
            if (data.status === 'active') {
                agentElement.classList.add('active');
            } else {
                agentElement.classList.remove('active');
            }
        }
    }

    // 显示错误消息
    showError(message) {
        const toast = document.getElementById('errorToast');
        const toastBody = document.getElementById('errorToastBody');
        
        if (toast && toastBody) {
            toastBody.textContent = message;
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        } else {
            alert(message);
        }
    }
}

// 全局应用实例
let app;

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    app = new QuantTraderApp();
});

// 导出给全局使用
window.app = app;
