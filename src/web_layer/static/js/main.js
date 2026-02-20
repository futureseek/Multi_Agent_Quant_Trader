/**
 * Multi-Agent Quant Trader 主JavaScript文件
 * 负责前端交互逻辑和API通信
 */

// 全局变量
let currentConversationId = null;
let socket = null;
let isSending = false;  // 防止重复提交标志
let currentStrategyCode = null;  // 当前策略代码

// DOM元素引用
const elements = {
    newConversationBtn: null,
    conversationList: null,
    messageInput: null,
    sendBtn: null,
    chatHistory: null,
    agentStatusItems: null,
    resultsPanel: null,
    strategyPanel: null,  // 新增：策略面板
    closeStrategyBtn: null,  // 新增：关闭策略按钮
    runBacktestBtn: null,  // 新增：运行回测按钮
    strategyCode: null  // 新增：代码显示区域
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

        // 新增：策略面板相关元素
        elements.strategyPanel = document.getElementById('strategy-panel');
        elements.closeStrategyBtn = document.getElementById('close-strategy');
        elements.runBacktestBtn = document.getElementById('run-backtest-btn');
        elements.strategyCode = document.getElementById('strategy-code');
        elements.resizer = document.getElementById('resizer');  // 新增：拖动分隔条
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

        // 关闭策略面板按钮
        elements.closeStrategyBtn?.addEventListener('click', () => {
            this.closeStrategyPanel();
        });

        // 运行回测按钮
        elements.runBacktestBtn?.addEventListener('click', () => {
            this.runBacktest();
        });

        // 拖动分隔条调整布局
        this.initResizer();
    }

    // 初始化分隔条拖动功能
    initResizer() {
        if (!elements.resizer) return;

        let isResizing = false;
        const contentWrapper = document.getElementById('content-wrapper');

        // 从localStorage恢复上次的比例
        const savedRatio = localStorage.getItem('panelRatio');
        if (savedRatio && contentWrapper.classList.contains('with-strategy')) {
            const leftPercent = parseFloat(savedRatio);
            contentWrapper.style.gridTemplateColumns = `${leftPercent}% 4px 1fr`;
        }

        // 鼠标按下开始拖动
        elements.resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            elements.resizer.classList.add('active');
            e.preventDefault(); // 防止选中文本
        });

        // 鼠标移动调整宽度
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const containerRect = contentWrapper.getBoundingClientRect();
            const newLeftWidth = e.clientX - containerRect.left;
            const containerWidth = containerRect.width;
            const leftPercent = (newLeftWidth / containerWidth) * 100;

            // 限制最小宽度 (20% - 80%)
            const clampedPercent = Math.max(20, Math.min(80, leftPercent));

            // 更新grid布局
            contentWrapper.style.gridTemplateColumns = `${clampedPercent}% 4px 1fr`;
        });

        // 鼠标松开停止拖动
        document.addEventListener('mouseup', (e) => {
            if (isResizing) {
                isResizing = false;
                elements.resizer.classList.remove('active');

                // 保存当前比例
                const computedStyle = getComputedStyle(contentWrapper);
                const gridTemplateColumns = computedStyle.gridTemplateColumns;
                const match = gridTemplateColumns.match(/^([\d.]+)%/);
                if (match) {
                    localStorage.setItem('panelRatio', match[1]);
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

        // 防止重复提交
        if (isSending) {
            console.log('正在发送中，请勿重复提交');
            return;
        }

        isSending = true;

        try {
            // 立即显示用户消息
            this.displayMessage({
                role: 'user',
                content: message,
                timestamp: new Date().toISOString()
            });

            // 清空输入框并禁用输入
            elements.messageInput.value = '';
            this.disableInputTemporarily();

            // 显示思考中状态
            const thinkingMessageId = this.displayThinkingMessage();

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
            
            // 移除思考中状态
            this.removeThinkingMessage(thinkingMessageId);

            // 重新启用输入
            this.enableInput();

            // 重置发送标志
            isSending = false;

            if (data.success && data.ai_response) {
                // 显示真实的AI回复
                this.displayMessage({
                    role: 'assistant',
                    content: data.ai_response.content,
                    timestamp: data.ai_response.timestamp,
                    agent: data.ai_response.agent,
                    intent: data.ai_response.intent
                });

                // 如果包含策略代码，显示在右侧面板
                if (data.ai_response.strategy_code) {
                    this.showStrategyPanel(data.ai_response.strategy_code);
                }
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

            // 出错时也要移除思考状态并重新启用输入
            const thinkingElement = document.querySelector('.thinking-message');
            if (thinkingElement) {
                thinkingElement.remove();
            }
            this.enableInput();

            // 重置发送标志
            isSending = false;
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

        // 处理消息内容：AI消息渲染Markdown，用户消息和错误消息保持原样
        let messageContent;
        if (!isUser && !isError) {
            // AI消息：解析Markdown并净化HTML（防止XSS）
            try {
                const rawHtml = marked.parse(message.content);
                messageContent = DOMPurify.sanitize(rawHtml);
            } catch (e) {
                console.error('Markdown解析失败:', e);
                messageContent = message.content;
            }
        } else {
            // 用户消息和错误消息：纯文本显示，保留换行
            messageContent = this.escapeHtml(message.content).replace(/\n/g, '<br>');
        }

        messageElement.innerHTML = `
            <div class="message-avatar ${avatarClass} ${isError ? 'error' : ''}">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                ${agentBadge}
                <div class="message-text ${isError ? 'error-text' : ''}">${messageContent}</div>
                <div class="message-time">${this.formatTime(message.timestamp)}</div>
            </div>
        `;

        elements.chatHistory.appendChild(messageElement);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;

        // 如果是AI消息，添加打字机效果
        if (!isUser && animate && !isError) {
            this.addTypingEffect(messageElement);
        }
    }

    // HTML转义（用于用户消息和错误消息）
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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

    // 临时禁用输入（发送消息时）
    disableInputTemporarily() {
        if (elements.messageInput) {
            elements.messageInput.disabled = true;
            elements.messageInput.placeholder = 'AI正在思考中...';
        }
        if (elements.sendBtn) {
            elements.sendBtn.disabled = true;
        }
    }

    // 显示思考中消息
    displayThinkingMessage() {
        if (!elements.chatHistory) return null;

        const thinkingMessageId = 'thinking-' + Date.now();
        const thinkingElement = document.createElement('div');
        thinkingElement.className = 'message assistant thinking-message fade-in';
        thinkingElement.id = thinkingMessageId;

        thinkingElement.innerHTML = `
            <div class="message-avatar assistant">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-meta">
                    <span class="agent-badge">智能助手</span>
                    <span class="thinking-indicator">思考中</span>
                </div>
                <div class="message-text thinking-text">
                    <div class="thinking-dots">
                        <span>正在分析您的问题</span>
                        <div class="dots">
                            <span class="dot"></span>
                            <span class="dot"></span>
                            <span class="dot"></span>
                        </div>
                    </div>
                </div>
                <div class="message-time">${this.formatTime(new Date().toISOString())}</div>
            </div>
        `;

        elements.chatHistory.appendChild(thinkingElement);
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;

        return thinkingMessageId;
    }

    // 移除思考中消息
    removeThinkingMessage(thinkingMessageId) {
        if (!thinkingMessageId) return;
        
        const thinkingElement = document.getElementById(thinkingMessageId);
        if (thinkingElement) {
            // 添加淡出效果
            thinkingElement.style.opacity = '0.5';
            setTimeout(() => {
                thinkingElement.remove();
            }, 200);
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

    // 显示策略面板
    showStrategyPanel(code) {
        console.log('🎯 显示策略面板');

        // 保存代码
        currentStrategyCode = code;

        // 显示代码
        if (elements.strategyCode) {
            elements.strategyCode.textContent = code;
            // 应用代码高亮
            if (typeof hljs !== 'undefined') {
                hljs.highlightElement(elements.strategyCode);
            }
        }

        // 显示策略面板
        if (elements.strategyPanel) {
            elements.strategyPanel.classList.remove('hidden');
        }

        // 添加with-strategy类到主容器
        const contentWrapper = document.getElementById('content-wrapper');
        if (contentWrapper) {
            contentWrapper.classList.add('with-strategy');
        }
    }

    // 关闭策略面板
    closeStrategyPanel() {
        console.log('❌ 关闭策略面板');

        // 隐藏策略面板
        if (elements.strategyPanel) {
            elements.strategyPanel.classList.add('hidden');
        }

        // 移除with-strategy类
        const contentWrapper = document.getElementById('content-wrapper');
        if (contentWrapper) {
            contentWrapper.classList.remove('with-strategy');
        }

        // 清空代码
        currentStrategyCode = null;
        if (elements.strategyCode) {
            elements.strategyCode.textContent = '';
        }
    }

    // 运行回测
    async runBacktest() {
        if (!currentStrategyCode) {
            this.showError('没有可运行的策略代码');
            return;
        }

        console.log('🚀 开始运行回测...');

        // 禁用按钮
        if (elements.runBacktestBtn) {
            elements.runBacktestBtn.disabled = true;
            elements.runBacktestBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>回测中...';
        }

        try {
            // 调用回测API
            const response = await fetch('/api/backtest/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_id: currentConversationId,
                    strategy_code: currentStrategyCode
                })
            });

            const data = await response.json();

            if (data.success) {
                console.log('✅ 回测完成');

                // 按钮保持禁用状态，显示"已回测"
                if (elements.runBacktestBtn) {
                    elements.runBacktestBtn.innerHTML = '<i class="fas fa-check me-2"></i>已回测';
                    // 不恢复disabled，保持禁用
                }

                // 显示回测结果（如果后端返回了结果数据）
                if (data.backtest_result) {
                    this.displayBacktestResult(data.backtest_result);
                }

                // 显示AI回复消息到聊天区域
                if (data.ai_response) {
                    this.displayMessage({
                        role: 'assistant',
                        content: data.ai_response.content || data.ai_response,
                        timestamp: new Date().toISOString(),
                        agent: 'handler_agent',
                        intent: 'backtest_result'
                    });
                }
            } else {
                this.showError(data.error || '回测失败');

                // 失败时恢复按钮
                if (elements.runBacktestBtn) {
                    elements.runBacktestBtn.disabled = false;
                    elements.runBacktestBtn.innerHTML = '<i class="fas fa-play me-2"></i>运行回测';
                }
            }

        } catch (error) {
            console.error('❌ 回测失败:', error);
            this.showError('回测失败: ' + error.message);

            // 异常时恢复按钮
            if (elements.runBacktestBtn) {
                elements.runBacktestBtn.disabled = false;
                elements.runBacktestBtn.innerHTML = '<i class="fas fa-play me-2"></i>运行回测';
            }
        }
    }

    // 显示回测结果
    displayBacktestResult(result) {
        console.log('📊 显示回测结果', result);

        // 显示结果区域
        const backtestResult = document.getElementById('backtest-result');
        if (backtestResult) {
            backtestResult.classList.remove('hidden');
        }

        // 更新指标
        if (result.total_return !== undefined) {
            const totalReturnEl = document.getElementById('total-return');
            if (totalReturnEl) {
                totalReturnEl.textContent = (result.total_return * 100).toFixed(2) + '%';
            }
        }

        if (result.sharpe_ratio !== undefined) {
            const sharpeRatioEl = document.getElementById('sharpe-ratio');
            if (sharpeRatioEl) {
                sharpeRatioEl.textContent = result.sharpe_ratio.toFixed(2);
            }
        }

        if (result.max_drawdown !== undefined) {
            const maxDrawdownEl = document.getElementById('max-drawdown');
            if (maxDrawdownEl) {
                maxDrawdownEl.textContent = (result.max_drawdown * 100).toFixed(2) + '%';
            }
        }

        if (result.win_rate !== undefined) {
            const winRateEl = document.getElementById('win-rate');
            if (winRateEl) {
                winRateEl.textContent = (result.win_rate * 100).toFixed(2) + '%';
            }
        }

        // 显示交易记录
        const tradesContainer = document.getElementById('trades-container');
        if (tradesContainer && result.trades) {
            tradesContainer.innerHTML = '';

            if (result.trades.length === 0) {
                tradesContainer.innerHTML = '<div class="text-center text-muted small">无交易记录</div>';
            } else {
                result.trades.forEach(trade => {
                    const tradeEl = document.createElement('div');
                    tradeEl.className = `trade-item trade-${trade.action}`;

                    const actionText = trade.action === 'buy' ? '买入' : '卖出';
                    const timeText = trade.time || '--';

                    tradeEl.innerHTML = `
                        <div class="trade-time">${timeText}</div>
                        <div class="trade-action">${actionText} ${trade.symbol || ''}</div>
                        <div>价格: ¥${trade.price?.toFixed(2) || '--'}</div>
                        <div>数量: ${trade.quantity || '--'}</div>
                        ${trade.profit !== undefined ? `<div>收益: ¥${trade.profit.toFixed(2)}</div>` : ''}
                    `;

                    tradesContainer.appendChild(tradeEl);
                });
            }
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
