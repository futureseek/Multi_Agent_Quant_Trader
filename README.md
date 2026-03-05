# Multi-Agent Quant Trader: 基于 LangGraph 的多智能体协同量化交易决策与回测系统

## 📋 启动准备

### 1. 配置API密钥

在 `config/` 目录下创建 `api_config.json` 文件：

```json
{
  "tushare_api": "YOUR_TUSHARE_API_TOKEN",
  "model": {
    "handler_agent":{
      "model_name": "MODEL_NAME",
      "api_key": "YOUR_API_KEY",
      "base_url": "YOUR_BASE_URL"
    },
    "strategy_agent":{
      "model_name": "MODEL_NAME",
      "api_key": "YOUR_API_KEY",
      "base_url": "YOUR_BASE_URL"
    },
    "data_service_agent":{
      "model_name": "MODEL_NAME",
      "api_key": "YOUR_API_KEY",
      "base_url": "YOUR_BASE_URL"
    }
  }
}
```

---

## 🚀 快速开始

### Step 1: 创建Conda环境
```bash
conda create -n MAtrader python=3.10 -y
conda activate MAtrader
```

#### Step 2: 安装Python依赖
```bash
# 安装Service Layer依赖（包含C++引擎所需的pybind11）
cd src/service_layer
pip install -r requirements.txt

# 安装Web Layer依赖
cd ../web_layer
pip install -r requirements.txt
```

**系统依赖**（需提前安装）：
- Ubuntu/Debian: `sudo apt-get install build-essential cmake`
- CentOS/RHEL: `sudo yum groupinstall "Development Tools" && sudo yum install cmake`
- macOS: `xcode-select --install && brew install cmake`

#### Step 3: 编译C++回测引擎
```bash
cd ../cpp_engine
mkdir -p build && cd build
cmake ..
make
```

**编译成功标志**：
```
[100%] Built target cpp_engine
```

生成文件：`src/cpp_engine/build/cpp_engine.cpython-310-x86_64-linux-gnu.so`

#### Step 4: 初始化RAG数据库（可选）
```bash
cd ../../scripts
python init_rag_db.py
```

#### Step 5: 启动Web服务
```bash
cd ../web_layer
python app.py
```

访问：`http://localhost:5000`

---

## 📂 目录结构

```
Multi_Agent_Quant_Trader/
├── config/                    # 全局配置文件
│   ├── api_config.json       # API密钥（需手动创建）
│   └── prompt_config.json    # Agent提示词
├── data/                      # 数据存储目录
│   ├── chroma_db/            # RAG向量数据库
│   └── debug_csv/            # 调试输出CSV
│       ├── daily_data_tool/  # 日线数据
│       └── trader_order/     # 交易记录
├── scripts/                   # 工具脚本
│   └── init_rag_db.py        # RAG数据库初始化
├── src/
│   ├── cpp_engine/           # [C++] 高性能回测引擎
│   │   ├── include/          # 头文件
│   │   ├── src/              # 源文件
│   │   ├── python/           # Python包装
│   │   ├── tests/            # 测试用例
│   │   └── build/            # 编译输出
│   ├── service_layer/        # [Python] 业务逻辑层
│   │   ├── agents/           # LangGraph智能体
│   │   ├── rag/              # RAG检索模块
│   │   ├── strategy/         # 策略定义
│   │   └── tools/            # 数据工具
│   └── web_layer/            # [Python] Web界面
│       ├── static/           # 前端资源
│       ├── templates/        # HTML模板
│       └── routes/           # API路由
├── tests/                     # 测试用例
├── docs/                      # 设计文档
├── README.md
└── update.log                 # 更新日志
```

---



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
├── CMakeLists.txt          # C++ 构建脚本
└── README.md
└── update.log              # 更新日志
```
