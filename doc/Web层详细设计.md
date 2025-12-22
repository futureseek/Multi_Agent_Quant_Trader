# Web层详细设计文档

## 需求分析

### 核心需求
1. **自适应布局**: 无回测结果时对话占据中间，有结果时左右分屏
2. **用户交互**: 左侧AI对话区域，支持多轮对话
3. **结果展示**: 右侧回测结果展示，包含图表和数据表格
4. **实时通信**: 与服务端实时通信，获取Agent响应和回测进度

### 功能拓展建议
1. **Agent状态指示**: 显示各Agent当前工作状态（分析中、决策中等）
2. **对话历史**: 支持对话记录保存和回顾
3. **策略参数调整**: 在对话过程中动态调整策略参数
4. **进度追踪**: 回测任务进度条和预估时间
5. **导出功能**: 支持回测报告导出为PDF/Excel
6. **快捷操作**: 常用问题模板、一键重新回测等

## 界面设计

### 布局方案

#### 1. 默认状态（无回测结果）
```
┌─────────────────────────────────────────────────────────┐
│                    顶部导航栏                            │
├────┬────────────────────────────────────────────────────┤
│侧边│                                                    │
│导航│                    AI对话区域                       │
│栏  │                  （居中显示）                       │
│    │                                                    │
│对话│  ┌─────────────────────────────────────────────┐   │
│列表│  │  Agent状态指示器                           │   │
│    │  ├─────────────────────────────────────────────┤   │
│+新建│  │  当前对话历史区域                           │   │
│    │  │                                             │   │
│    │  │                                             │   │
│    │  ├─────────────────────────────────────────────┤   │
│    │  │  输入框 + 发送按钮                         │   │
│    │  └─────────────────────────────────────────────┘   │
│    │                                                    │
└────┴────────────────────────────────────────────────────┘
```

#### 2. 分屏状态（有回测结果）
```
┌─────────────────────────────────────────────────────────┐
│                    顶部导航栏                            │
├────┬────────────────────┬────────────────────────────────┤
│侧边│      AI对话区域    │        回测结果区域            │
│导航│                    │                                │
│栏  │ ┌────────────────┐ │ ┌────────────────────────────┐ │
│    │ │ Agent状态指示器│ │ │    结果概览面板            │ │
│对话│ ├────────────────┤ │ ├────────────────────────────┤ │
│列表│ │ 当前对话历史   │ │ │    收益率曲线图            │ │
│    │ │                │ │ │                            │ │
│+新建│ │                │ │ ├────────────────────────────┤ │
│    │ ├────────────────┤ │ │    关键指标表格            │ │
│    │ │ 输入框+发送按钮│ │ ├────────────────────────────┤ │
│    │ └────────────────┘ │ │    交易记录列表            │ │
│    │                    │ └────────────────────────────┘ │
└────┴────────────────────┴────────────────────────────────┘
```

## 技术架构设计

### 前端技术栈
- **框架**: Flask + Jinja2 (服务端渲染) + JavaScript (客户端交互)
- **样式**: Bootstrap 5 + 自定义CSS
- **图表**: Chart.js / ECharts (支持收益率曲线、回撤图、持仓分布等)
- **表格**: DataTables.js (支持排序、搜索、分页)
- **实时通信**: WebSocket (Socket.IO)
- **图标**: Font Awesome / Lucide Icons

### 组件设计

#### 1. 侧边导航组件 (SidebarComponent)
```javascript
class SidebarComponent {
    // 对话管理
    createNewConversation()
    loadConversation(conversationId)
    deleteConversation(conversationId)
    
    // 对话列表渲染
    renderConversationList()
    updateConversationTitle(conversationId, title)
    
    // 状态管理
    setActiveConversation(conversationId)
    saveConversationOrder()
}
```

#### 2. AI对话组件 (ChatComponent)
```javascript
class ChatComponent {
    constructor(conversationId) {
        this.conversationId = conversationId
    }
    
    // 消息发送
    sendMessage(message, messageType)
    
    // 消息接收和渲染
    receiveMessage(response, agentType)
    
    // Agent状态更新
    updateAgentStatus(agentId, status)
    
    // 当前对话历史管理
    loadConversationHistory(conversationId)
    clearCurrentChat()
    
    // 结果展示切换
    toggleResultsPanel(show)
}
```

#### 3. 回测结果组件 (BacktestResultComponent)
```javascript
class BacktestResultComponent {
    // 结果数据从消息中解析
    parseResultsFromMessage(messageContent)
    
    // 图表渲染
    renderPerformanceChart(chartData)
    renderDrawdownChart(chartData)
    renderPositionChart(chartData)
    
    // 表格渲染
    renderMetricsTable(metricsData)
    renderTradeHistory(tradesData)
    
    // 导出功能
    exportCurrentResults()
}
```

## 接口设计

### RESTful API接口

#### 1. 对话管理接口
```
POST /api/conversations/create
请求体: {
    "title": "茅台投资分析" // 可选，系统可自动生成
}
响应: {
    "conversation_id": "uuid",
    "title": "茅台投资分析",
    "created_at": "2025-12-21T23:30:00Z"
}

GET /api/conversations/list
响应: {
    "conversations": [
        {
            "conversation_id": "uuid1",
            "title": "茅台投资分析",
            "last_message_time": "2025-12-21T23:30:00Z",
            "message_count": 5
        }
    ]
}

GET /api/conversations/{conversation_id}/messages
响应: {
    "conversation_id": "uuid",
    "messages": [
        {
            "message_id": "msg_uuid",
            "role": "user",
            "content": "帮我分析一下茅台",
            "timestamp": "2025-12-21T23:30:00Z"
        },
        {
            "message_id": "msg_uuid2", 
            "role": "assistant",
            "agent_type": "data_analyst",
            "content": "根据我的分析...",
            "timestamp": "2025-12-21T23:31:00Z",
            "chart_data": {...}, // 图表数据
            "table_data": {...}  // 表格数据
        }
    ]
}

DELETE /api/conversations/{conversation_id}
响应: {
    "success": true,
    "message": "对话已删除"
}
```

#### 2. 消息传输接口
```
POST /api/messages/send
请求体: {
    "conversation_id": "uuid",
    "message": "帮我分析一下茅台的投资价值"
}
响应: {
    "message_id": "msg_uuid",
    "conversation_id": "uuid",
    "agents_triggered": ["data_analyst", "risk_manager"],
    "estimated_time": 30
}

GET /api/messages/{message_id}/status
响应: {
    "message_id": "msg_uuid",
    "status": "processing", // processing, completed, failed
    "current_agent": "data_analyst",
    "progress": 60,
    "partial_response": "正在分析技术指标..."
}
```



### WebSocket事件设计

```javascript
// 客户端发送
socket.emit('join_conversation', {conversation_id: 'uuid'});
socket.emit('send_message', {message: 'text', conversation_id: 'uuid'});

// 服务端推送
socket.on('agent_status_update', {
    agent_id: 'data_analyst',
    status: 'analyzing',
    progress: 30,
    message: '正在分析K线数据...'
});

socket.on('partial_response', {
    agent_id: 'data_analyst',
    partial_content: '根据技术分析...',
    is_complete: false
});

socket.on('backtest_progress', {
    backtest_id: 'bt_uuid',
    progress: 45,
    current_date: '2024-03-15',
    estimated_remaining: 120
});
```

## 页面组织内容

### 1. 主页面 (index.html)
```html
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Agent Quant Trader</title>
    <!-- CSS引入 -->
</head>
<body>
    <!-- 顶部导航栏 -->
    <nav class="navbar">
        <div class="navbar-brand">量化交易AI助手</div>
        <div class="navbar-actions">
            <button id="export-results">导出结果</button>
        </div>
    </nav>
    
    <!-- 主内容区域 -->
    <div id="main-container" class="container-fluid">
        <!-- 侧边导航栏 -->
        <div id="sidebar" class="sidebar">
            <div class="sidebar-header">
                <button id="new-conversation" class="btn-new-chat">
                    <i class="icon-plus"></i> 新建对话
                </button>
            </div>
            <div class="sidebar-content">
                <div id="conversation-list" class="conversation-list">
                    <!-- 对话列表项 -->
                    <!-- <div class="conversation-item active" data-conversation-id="uuid">
                        <div class="conversation-title">茅台投资分析</div>
                        <div class="conversation-meta">
                            <span class="message-count">5条消息</span>
                            <button class="btn-delete">×</button>
                        </div>
                    </div> -->
                </div>
            </div>
        </div>
        
        <!-- AI对话区域 -->
        <div id="chat-panel" class="chat-panel">
            <div id="agent-status" class="agent-status-bar">
                <!-- Agent状态指示器 -->
                <div class="agent-status-item" data-agent="data_analyst">数据分析师</div>
                <div class="agent-status-item" data-agent="risk_manager">风控官</div>
                <div class="agent-status-item" data-agent="portfolio_manager">基金经理</div>
            </div>
            <div id="chat-history" class="chat-history">
                <!-- 对话记录 -->
                <div class="welcome-message">
                    <h3>欢迎使用量化交易AI助手</h3>
                    <p>您可以询问投资策略、技术分析、风险评估等问题，我们的AI团队将为您提供专业分析。</p>
                </div>
            </div>
            <div id="chat-input" class="chat-input-area">
                <div class="input-group">
                    <input type="text" id="message-input" placeholder="请输入您的问题...">
                    <button id="send-btn" class="btn-send">发送</button>
                </div>
            </div>
        </div>
        
        <!-- 回测结果区域 -->
        <div id="results-panel" class="results-panel hidden">
            <div class="results-header">
                <h3>回测结果</h3>
                <div class="results-actions">
                    <button id="refresh-results">刷新</button>
                    <button id="export-pdf">导出PDF</button>
                </div>
            </div>
            <div class="results-content">
                <!-- 结果概览 -->
                <div id="performance-summary" class="performance-summary">
                    <!-- 关键指标卡片 -->
                </div>
                
                <!-- 图表区域 -->
                <div id="charts-container" class="charts-container">
                    <canvas id="equity-chart"></canvas>
                    <canvas id="drawdown-chart"></canvas>
                </div>
                
                <!-- 数据表格 -->
                <div id="tables-container" class="tables-container">
                    <table id="metrics-table" class="table">
                        <!-- 指标表格 -->
                    </table>
                    <table id="trades-table" class="table">
                        <!-- 交易记录表格 -->
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- JavaScript引入 -->
</body>
</html>
```

### 2. 样式设计要点
```css
/* 自适应布局 */
#main-container {
    display: flex;
    height: calc(100vh - 60px);
    transition: all 0.3s ease;
}

#chat-panel {
    flex: 1;
    transition: all 0.3s ease;
}

#results-panel {
    flex: 1;
    border-left: 1px solid #e0e0e0;
    transition: all 0.3s ease;
}

#results-panel.hidden {
    flex: 0;
    width: 0;
    overflow: hidden;
}

/* Agent状态指示器 */
.agent-status-item {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
    margin-right: 8px;
}

.agent-status-item.active {
    background: #007bff;
    color: white;
    animation: pulse 2s infinite;
}
```

## 用户体验优化

### 1. 交互反馈
- **输入状态**: 显示"AI正在思考..."加载动画
- **进度指示**: Agent工作进度条和预估时间
- **错误处理**: 友好的错误提示和重试机制
- **响应式设计**: 支持不同屏幕尺寸自适应

### 2. 性能优化
- **懒加载**: 图表和表格数据按需加载
- **缓存策略**: 对话历史和结果数据本地缓存
- **分页加载**: 大量交易记录分页展示
- **压缩传输**: 图表数据压缩传输

### 3. 可访问性
- **键盘导航**: 支持Tab键和回车键操作
- **屏幕阅读器**: 适当的ARIA标签
- **对比度**: 确保文字和背景对比度符合标准

## 开发优先级

### 第一阶段 (MVP)
1. 基本对话界面和WebSocket连接
2. 自适应布局切换
3. 简单的结果展示（表格+基础图表）

### 第二阶段 (增强功能)
1. Agent状态指示和进度追踪
2. 丰富的图表类型和交互
3. 对话历史保存

### 第三阶段 (完善体验)
1. 导出功能
2. 快捷操作和模板
3. 性能优化和错误处理

这个设计方案既满足了您的核心需求，又为未来的功能扩展预留了空间。界面简洁直观，技术选型稳健可靠，适合快速开发和迭代。
