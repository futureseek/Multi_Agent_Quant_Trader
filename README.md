# Multi-Agent Quant Trader: 基于 LangGraph 与高性能 C++ 引擎的混合架构交易系统


## 启动需要
密钥都是写在文件中，所以干脆都没有添加到git推送上去，需要在config目录下创建
api_config.json文件，写入以下内容：
```json
{
  "tushare_api": "",
  "model": {
    "handler_agent":{
      "model_name": "",
      "api_key": "",
      "base_url": ""
    },
    "strategy_agent":{
      "model_name": "",
      "api_key": "",
      "base_url": ""
    },
    "data_service_agent":{
      "model_name": "",
      "api_key": "",
      "base_url": ""
    }
  }
}

```



> **2025 本科毕业设计课题** 

随着金融科技（FinTech）的发展，量化交易正从“数据挖掘”向“AI 智能决策”演进。目前的 AI 交易研究普遍存在两大痛点：
1.  **决策模式单一**：缺乏像真实金融机构中分析师、风控官、基金经理那样的“多角色制衡”机制。
2.  **回测性能瓶颈**：纯 Python 环境在处理高频历史数据撮合时效率低下，回测性能低。

本项目旨在设计并实现一个**“存算分离、软硬结合”**的智能交易系统。通过 **Python + LangGraph** 模拟机构投委会的复杂决策流程，通过 **C++ + Pybind11** 构建高性能离散事件仿真引擎，兼顾了逻辑推理的深度与回测系统的严谨性。

## 🏗️ 系统架构 (System Architecture)

本系统采用 **Python (大脑) + C++ (躯干)** 的混合架构设计：

### 1. 应用决策层 
*   **框架**: `LangGraph`, `LangChain`
*   **功能**:
    *   **多智能体协作 (Multi-Agent)**: 模拟数据情报员、技术分析师、风控官、基金经理的角色博弈。
    *   **RAG 增强检索**: 使用 `ChromaDB` 存储历史财经新闻向量。
    *   **时序感知**: 严格限制 Agent 只能检索当前仿真时间点之前的舆情，防止数据泄露。

### 2. 核心执行层 (The Engine - C++)
*   **技术**: `C++17`, `Pybind11`, `CMake`
*   **功能**:
    *   **黑盒交易所**: 维护 Order Book (订单簿) 和 Portfolio (账户持仓)。
    *   **高性能撮合**: 基于内存的极速回测，支持滑点模拟和交易成本计算。
    *   **时间机器**: 控制全局仿真时钟，按日/分钟步进，驱动 Python 层决策。

### 3. 数据层
*   **结构化数据**: CSV/Parquet 格式的历史 K 线数据（供 C++ 引擎只读）。
*   **非结构化数据**: 本地向量数据库（供 Python Agent 检索）。
*   **结果存储**: `SQLite` 数据库，用于存储交易日志和 Agent 的思考链路（Reasoning Trace）。


## 技术选型
- 开发环境：WSL2+Ubuntu20.04
- 核心语言：python3.10、C++17
- AI框架：LangGraph
- 数据库：ChromaDB，SQLite
- 桥接层：pybind11

## 目录结构规划 (Directory Structure)

```shell
Multi-Agent-Quant-Trader/
├── cmake/                  # CMake 构建配置
├── config/                 # 全局配置文件 (json，包括api密钥、参数等内容)
│   └── api_config.json     # 密钥文件
├── stroage/                # 本地数据存储
├── docs/                   # 设计文档与论文素材
├── src/
│   ├── cpp_core/           # [C++ 模块] 交易引擎核心
│   │   ├── include/        # 头文件 (Engine.h, Portfolio.h)
│   │   ├── src/            # 实现文件
│   │   └── bindings/       # Pybind11 接口定义
│   └── python_app/         # [Python 模块] 业务逻辑
│       ├── agents/         # LangGraph 节点定义 (Analyst, Manager...)
│       ├── rag/            # 向量检索与 News 处理
│       └── main.py         # 系统入口
├── tests/                  # 测试用例
│   ├── cpp_tests/          # GoogleTest 单元测试
│   └── python_tests/       # PyTest 流程测试
├── CMakeLists.txt          # C++ 构建脚本
└── README.md
```
