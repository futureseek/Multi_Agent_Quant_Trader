# RAG链路设计文档

## 设计概述

本文档定义了**RAG（检索增强生成）链路**在量化交易系统中的应用设计，通过向量数据库 + LLM实现智能选股和知识问答功能。

### 核心理念
- **向量化存储**: 将股票信息、财务数据、新闻研报向量化存储
- **语义检索**: 基于用户问题检索相关知识
- **LLM增强**: 结合检索结果生成准确答案
- **多场景支持**: 选股、问答、数据分析

### 应用场景
1. **智能选股**: "找市盈率小于20的科技小盘股"
2. **知识问答**: "贵州茅台的主营业务是什么？"
3. **数据查询**: "最近有哪些行业有利好消息？"
4. **投资建议**: "当前市场环境下适合配置什么板块？"

**核心设计**: 所有查询统一由 `RAGQueryAgent` 处理，LLM自动判断返回格式（选股列表 或 自然语言答案）

---

## 整体架构

### 系统架构图

```
┌──────────────────────────────────────────────────────────────┐
│                      HandlerAgent                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  意图识别                                              │ │
│  │  - rag_query        → RAG查询链路（统一入口）          │ │
│  │  - backtest_request  → 原有回测流程                    │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ↓
        ┌────────────────────────────────────┐
        │      RAGQueryAgent                 │
        │  (统一处理选股和问答)              │
        │  - 智能选股 → 返回股票列表         │
        │  - 知识问答 → 返回自然语言答案     │
        └──────────────┬─────────────────────┘
                       ↓
        ┌────────────────────────────────┐
        │     RAG核心组件层              │
        └────────────────────────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    ↓                  ↓                  ↓
┌─────────┐    ┌─────────────┐    ┌──────────┐
│ChromaDB │    │ Embedding   │    │ LLM      │
│向量DB   │    │ 模型        │    │ (Claude) │
└────┬────┘    └──────┬──────┘    └────┬─────┘
     │                │                │
     └────────────────┼────────────────┘
                      ↓
            ┌─────────────────────┐
            │   数据源层          │
            └─────────────────────┘
                      │
    ┌─────────────────┼──────────────────┐
    ↓                 ↓                  ↓
┌─────────┐    ┌──────────┐    ┌──────────┐
│Tushare  │    │财经网站  │    │公告/研报 │
│API      │    │爬虫      │    │API       │
└─────────┘    └──────────┘    └──────────┘
```

---

## 核心组件设计

### 1. 向量存储层 (ChromaDB)

#### 1.1 数据结构

```python
# vector_store.py

class StockVectorStore:
    """股票知识向量存储"""

    def __init__(self, persist_dir: str = "./data/chroma_db"):
        # 持久化配置
        self.client = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir
            )
        )

        # 初始化Embedding模型
        self.embedder = SentenceTransformer('shibing624/text2vec-base-chinese')

        # 创建多个collection（分类存储）
        self.collections = {
            'basic_info': self._create_collection('stock_basic_info'),
            'financial': self._create_collection('stock_financial'),
            'news': self._create_collection('market_news'),
            'reports': self._create_collection('research_reports'),
            'announcements': self._create_collection('announcements')
        }

    def _create_collection(self, name: str):
        """创建collection"""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}  # 余弦相似度
        )

    def add_documents(self, collection_name: str, documents: list, metadatas: list, ids: list):
        """批量添加文档"""
        self.collections[collection_name].add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, collection_names: list = None, top_k: int = 5):
        """跨collection检索"""
        if collection_names is None:
            collection_names = list(self.collections.keys())

        results = []
        for name in collection_names:
            collection_results = self.collections[name].query(
                query_texts=[query],
                n_results=top_k
            )
            results.extend(collection_results['documents'][0])

        return results
```

#### 1.2 Collection设计

| Collection名称 | 用途 | 数据量 | 更新频率 |
|----------------|------|--------|----------|
| `stock_basic_info` | 股票基本信息 | ~5000 | 每周 |
| `stock_financial` | 财务指标 | ~125万/年 | 每日 |
| `market_news` | 市场新闻 | ~100/天 | 每日 |
| `research_reports` | 研究报告 | ~10/天 | 每日 |
| `announcements` | 公告信息 | ~50/天 | 每日 |

---

### 2. 数据源层

#### 2.1 Tushare集成

```python
# data_collector.py

class StockDataCollector:
    """股票数据收集器"""

    def __init__(self, tushare_token: str):
        ts.set_token(tushare_token)
        self.pro = ts.pro_api()

    def collect_basic_info(self) -> tuple[list, list, list]:
        """
        收集股票基本信息

        Returns:
            (documents, metadatas, ids)
        """
        stock_list = self.pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,market,list_date'
        )

        documents = []
        metadatas = []
        ids = []

        for _, row in stock_list.iterrows():
            doc = f"""
            股票代码: {row['ts_code']}
            股票名称: {row['name']}
            所属区域: {row['area']}
            所属行业: {row['industry']}
            交易市场: {row['market']}
            上市日期: {row['list_date']}
            """.strip()

            documents.append(doc)
            metadatas.append({
                'symbol': row['ts_code'],
                'name': row['name'],
                'industry': row['industry'],
                'area': row['area'],
                'market': row['market']
            })
            ids.append(row['ts_code'])

        return documents, metadatas, ids

    def collect_financial_data(self, symbols: list = None) -> tuple:
        """
        收集财务指标

        Returns:
            (documents, metadatas, ids)
        """
        # 获取最新交易日
        trade_date = self.pro.trade_cal(
            exchange='SSE',
            start_date='20200101',
            end_date=datetime.now().strftime('%Y%m%d')
        ).tail(1)['cal_date'].values[0]

        # 获取每日基本面指标
        df = self.pro.daily_basic(
            ts_code=symbols,
            trade_date=trade_date,
            fields='ts_code,trade_date,pe,pb,ps,dv_ratio,total_mv,circ_mv'
        )

        documents = []
        metadatas = []
        ids = []

        for _, row in df.iterrows():
            doc = f"""
            {row['ts_code']} 最新财务指标 ({row['trade_date']}):
            市盈率(PE): {row['pe']}
            市净率(PB): {row['pb']}
            市销率(PS): {row['ps']}
            股息率: {row['dv_ratio']}
            总市值(亿元): {row['total_mv']}
            流通市值(亿元): {row['circ_mv']}
            """.strip()

            documents.append(doc)
            metadatas.append({
                'symbol': row['ts_code'],
                'date': row['trade_date'],
                'pe': row['pe'],
                'pb': row['pb'],
                'total_mv': row['total_mv']
            })
            ids.append(f"{row['ts_code']}_{row['trade_date']}")

        return documents, metadatas, ids
```

#### 2.2 数据源设计

| 数据源 | 类型 | 获取方式 | 字段示例 |
|--------|------|----------|----------|
| **Tushare** | API | pro.stock_basic | ts_code, name, industry |
| **Tushare** | API | pro.daily_basic | pe, pb, total_mv |
| **东方财富** | 爬虫 | requests + BeautifulSoup | 新闻标题、正文 |
| **巨潮资讯** | API | 提供的API接口 | 公告全文 |
| **雪球** | 爬虫 | API/爬虫 | 舆情数据 |

---

### 3. RAGQueryAgent（统一查询入口）

#### 3.1 统一查询流程

```
用户: "找市盈率小于20的科技小盘股" 或 "宁德时代的主营业务是什么？"
  ↓
1. 向量检索
   - 查询: 用户原始问题
   - 检索范围: 跨所有collection（basic_info, financial, news等）
   - 返回: Top-K相关文档
  ↓
2. LLM智能分析
   - 输入: 用户问题 + 检索到的参考文档
   - LLM自动判断问题类型：
     * 选股类 → 返回JSON格式股票列表
     * 问答类 → 返回自然语言答案
  ↓
3. 结果返回
   - 选股结果: 平安银行、招商银行...
   - 问答结果: 宁德时代主营动力电池系统...
```

#### 3.2 代码设计

```python
# rag_query_agent.py

class RAGQueryAgent:
    """RAG查询Agent - 统一处理选股和问答"""

    def __init__(self, vector_store, llm):
        self.vector_store = vector_store
        self.llm = llm

    def query(self, user_input: str, top_k: int = 10) -> dict:
        """
        统一查询接口 - LLM自动判断返回格式

        Args:
            user_input: 用户问题（选股或问答）
            top_k: 返回结果数量

        Returns:
            {
                'success': True,
                'query_type': 'stock_selection',  # 或 'knowledge_query'
                'result': {...},  # 根据类型返回不同结构
                'sources': [...]  # 检索到的参考文档
            }
        """
        # 1. 向量检索（跨所有collection）
        search_results = self.vector_store.search(
            query=user_input,
            collection_names=None,  # 全部collection
            top_k=top_k * 3  # 多检索一些给LLM筛选
        )

        # 2. 构建统一prompt（让LLM自动判断类型）
        prompt = self._build_unified_prompt(user_input, search_results, top_k)

        # 3. LLM生成响应
        response = self.llm.invoke(prompt)

        # 4. 解析结果（自动识别JSON或自然语言）
        return self._parse_response(response, search_results)

    def _build_unified_prompt(self, question: str, context_docs: list, top_k: int) -> str:
        """构建统一prompt - LLM自动判断问题类型"""

        context_text = "\n\n".join([
            f"【参考文档{i+1}】\n{doc}"
            for i, doc in enumerate(context_docs[:30])
        ])

        template = """
你是一个专业的智能投资助手。请根据以下知识库内容回答用户问题：

参考文档:
{context}

用户问题: {question}

请根据问题类型选择合适的回答格式：

**类型1：选股类问题**
如："找..."、"筛选..."、"推荐..."、"哪些股票..."
请返回JSON格式：
```json
{{
    "query_type": "stock_selection",
    "stocks": [
        {{
            "symbol": "000001.SZ",
            "name": "平安银行",
            "reason": "市盈率5.2小于20，属于金融行业，符合所有条件"
        }}
    ]
}}
```

**类型2：问答类问题**
如："什么是..."、"主营..."、"介绍..."、"如何..."
请返回JSON格式：
```json
{{
    "query_type": "knowledge_query",
    "answer": "详细的自然语言解答..."
}}
```

请严格返回上述JSON格式之一，不要添加其他内容。
"""

        return template.format(
            context=context_text,
            question=question
        )

    def _parse_response(self, response, sources: list) -> dict:
        """解析LLM响应"""
        import json

        try:
            # 提取JSON
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            result = json.loads(json_str)

            return {
                'success': True,
                'query_type': result.get('query_type'),
                'result': result,
                'sources': [doc[:100] + '...' for doc in sources[:5]]
            }

        except Exception as e:
            # 降级：如果JSON解析失败，返回原始文本
            return {
                'success': True,
                'query_type': 'knowledge_query',
                'result': {'answer': response.content},
                'sources': [doc[:100] + '...' for doc in sources[:5]]
            }
```

#### 3.3 调用示例

```python
# 示例1：智能选股
result1 = rag_agent.query("找市盈率小于15的银行股")
# → 返回: {'query_type': 'stock_selection', 'stocks': [...]}

# 示例2：知识问答
result2 = rag_agent.query("贵州茅台的主营业务是什么？")
# → 返回: {'query_type': 'knowledge_query', 'answer': '贵州茅台主营...'}

# 示例3：混合查询
result3 = rag_agent.query("推荐几家市盈率低的新能源公司，并说明原因")
# → LLM自动判断为选股类型，返回股票列表 + 详细理由
```

---

### 4. HandlerAgent集成

#### 4.1 意图识别扩展

```python
# handler_agent.py (修改)

async def _analyze_intent_node(self, state: AgentState) -> AgentState:
    """意图分析节点"""
    try:
        print("🧠 分析用户意图...")
        state["current_step"] = "analyzing_intent"

        user_input = state["user_input"].lower()

        # RAG查询关键词（统一入口）
        rag_keywords = ["选股", "筛选", "找", "推荐", "什么是", "主营", "业务", "介绍", "哪些"]
        # 回测关键词
        backtest_keywords = ["回测", "策略", "收益", "夏普", "回测结果"]

        if any(keyword in user_input for keyword in rag_keywords):
            intent = "rag_query"  # 统一的RAG查询入口
        elif any(keyword in user_input for keyword in backtest_keywords):
            intent = "backtest_request"
        else:
            intent = "general_chat"

        state["analysis_result"] = intent
        return state

    except Exception as e:
        print(f"❌ 意图分析失败: {e}")
        state["error"] = f"意图分析异常: {str(e)}"
        return state
```

#### 4.2 路由决策扩展

```python
def _route_after_intent(self, state: AgentState) -> str:
    """意图分析后的路由决策（新增RAG分支）"""
    intent = state.get("analysis_result")

    print(f"🎯 路由决策: 意图={intent}")

    if intent == "backtest_request":
        return "fetch_data"  # 回测链路
    elif intent == "rag_query":
        return "rag_query"   # RAG查询链路（统一入口）
    else:
        return "generate_response"  # 普通对话
```

#### 4.3 新增RAG查询节点

```python
async def _rag_query_node(self, state: AgentState) -> AgentState:
    """RAG查询节点 - 统一处理选股和问答"""
    try:
        print("🔍 执行RAG查询...")
        state["current_step"] = "rag_query"

        user_input = state["user_input"]

        # 调用RAGQueryAgent（统一入口）
        result = rag_query_agent.query(
            user_input=user_input,
            top_k=10
        )

        if result["success"]:
            # 根据查询类型格式化输出
            query_type = result.get("query_type")
            result_data = result.get("result")

            if query_type == "stock_selection":
                # 选股结果格式化
                stocks = result_data.get("stocks", [])
                response_text = f"## 📊 选股结果\n\n"
                response_text += f"筛选条件: {user_input}\n\n"

                for i, stock in enumerate(stocks[:10], 1):
                    response_text += f"{i}. **{stock['symbol']}** - {stock['name']}\n"
                    response_text += f"   {stock['reason']}\n"

                state["final_response"] = response_text

            elif query_type == "knowledge_query":
                # 问答结果格式化
                answer = result_data.get("answer", "")
                sources = result.get("sources", [])

                response_text = f"## 📖 知识库查询结果\n\n"
                response_text += f"{answer}\n\n"

                if sources:
                    response_text += f"**参考来源：**\n"
                    for i, source in enumerate(sources[:3], 1):
                        response_text += f"{i}. {source}\n"

                state["final_response"] = response_text
        else:
            state["error"] = "RAG查询失败"

        return state

    except Exception as e:
        print(f"❌ RAG查询失败: {e}")
        state["error"] = f"RAG查询异常: {str(e)}"
        return state
```

---

## 技术选型

### 向量数据库

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| **ChromaDB** | 轻量、Python原生、易上手 | 性能一般 | ✅ 选择 |
| Qdrant | 高性能、Rust编写 | 学习曲线 | - |
| Milvus | 生产级、功能全 | 部署复杂 | - |
| Pinecone | 托管服务 | 收费、数据出境 | - |

**最终选择**: ChromaDB
- 轻量级，适合单用户场景
- Python原生，集成简单
- 支持持久化存储

### Embedding模型

| 模型 | 语言 | 大小 | 性能 | 选择 |
|------|------|------|------|------|
| **text2vec-base-chinese** | 中文 | 100MB | 中等 | ✅ 初期 |
| bge-large-zh-v1.5 | 中文 | 1.3GB | 优秀 | - |
| m3e-base | 多语言 | 400MB | 良好 | - |

**最终选择**: text2vec-base-chinese
- 轻量级，快速部署
- 中文语料优化
- 后续可升级到bge-large-zh-v1.5

---

## 实现计划

### Phase 1: 基础设施搭建 (1周)

**任务清单**:
- [ ] 安装依赖
  ```bash
  pip install chromadb==0.4.22
  pip install sentence-transformers
  pip install langchain-community
  pip install tushare
  ```

- [ ] 创建向量存储模块
  - `src/service_layer/rag/vector_store.py`
  - 实现ChromaDB初始化
  - 创建collection结构

- [ ] 创建数据收集器
  - `src/service_layer/rag/data_collector.py`
  - Tushare集成
  - 测试基础信息收集

### Phase 2: Agent实现 (1周)

**任务清单**:
- [ ] RAGQueryAgent（统一查询入口）
  - `src/service_layer/agents/rag_query_agent.py`
  - query()统一方法
  - LLM自动判断返回格式
  - 支持选股和问答两种场景

- [ ] HandlerAgent集成
  - 扩展意图识别（rag_query统一入口）
  - 新增rag_query_node节点
  - 路由决策更新

### Phase 3: 数据构建 (持续)

**任务清单**:
- [ ] 构建知识库
  - 收集A股基础信息 (5000+只股票)
  - 收集财务数据 (PE/PB/市值)
  - 收集行业分类

- [ ] 数据更新机制
  - 定时更新任务
  - 增量更新逻辑
  - 数据质量检查

### Phase 4: 优化完善 (按需)

**任务清单**:
- [ ] 检索优化
  - 混合检索 (向量+关键词)
  - 结果重排序
  - 缓存机制

- [ ] 性能优化
  - 批量插入
  - 异步更新
  - 索引优化

---

## 关键技术点

### 1. 检索优化策略

```python
def hybrid_search(query: str, top_k: int = 10):
    """混合检索策略"""

    # 1. 向量检索（语义相似）
    vector_results = vector_search(query, top_k=top_k * 2)

    # 2. 关键词检索（精确匹配）
    keyword_results = keyword_search(query, top_k=top_k * 2)

    # 3. 融合排序
    final_results = merge_and_rerank(
        vector_results,
        keyword_results,
        top_k=top_k
    )

    return final_results
```

### 2. 知识库维护

```python
class KnowledgeBaseManager:
    """知识库管理"""

    def update_basic_info(self):
        """每日更新基础信息"""
        # 增量更新新上市公司
        # 更新退市股票状态

    def update_financial_data(self):
        """交易日更新财务数据"""
        # 更新PE/PB/市值等指标

    def add_news(self, days: int = 1):
        """每日添加新闻"""
        # 爬取当日新闻
        # 向量化并存储
```

---

## 成本估算

### 硬件需求

**开发阶段**:
- 内存: 8GB+
- 磁盘: 50GB (向量数据)

**生产环境**:
- 内存: 16GB+ (支持并发检索)
- 磁盘: 200GB+ (包含历史数据)

### 数据量估算

```
基础信息: 5000股票 × 2KB ≈ 10MB
财务数据: 5000股票 × 250交易日 × 1KB ≈ 1.25GB/年
新闻数据: 100条/天 × 2KB ≈ 73MB/年
```

---

## 潜在问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| **检索不准确** | 混合检索 + 结果重排序 |
| **数据更新滞后** | 定时任务 + 增量更新 |
| **LLM幻觉** | 提供参考文档 + 要求标注来源 |
| **性能瓶颈** | 向量索引优化 + 缓存 |
| **股票名称消歧** | 模糊匹配 + 人工确认 |

---

## 数据流示例

### 示例1：智能选股

```
输入: "帮我找市盈率小于15的银行股"

流程:
1. HandlerAgent意图识别 → rag_query
2. RAGQueryAgent.query()
3. ChromaDB检索
   - 查询: "市盈率小于15的银行股"
   - 检索: basic_info + financial（全collection检索）
   - 返回: 30个候选
4. LLM分析并判断为选股类型
5. 返回选股结果:
   - 平安银行: PE=5.2
   - 招商银行: PE=6.1
   - ...
```

### 示例2：知识问答

```
输入: "宁德时代的主营业务是什么？"

流程:
1. HandlerAgent意图识别 → rag_query
2. RAGQueryAgent.query()
3. ChromaDB检索
   - 查询: "宁德时代主营业务"
   - 返回: 5个相关文档
4. LLM分析并判断为问答类型
5. 返回: "宁德时代（CATL）主营..."
```

### 示例3：混合查询

```
输入: "推荐几家低估值的新能源公司，并介绍它们的主营业务"

流程:
1. HandlerAgent意图识别 → rag_query
2. RAGQueryAgent.query()
3. ChromaDB跨collection检索
4. LLM综合分析：
   - 判断为选股类型
   - 同时在返回结果中包含业务介绍
5. 返回结构化选股结果 + 详细说明
```

---

## 文件结构

```
src/service_layer/
├── rag/
│   ├── __init__.py
│   ├── vector_store.py          # 向量存储
│   ├── data_collector.py         # 数据收集
│   └── knowledge_base.py         # 知识库管理
│
└── agents/
    ├── rag_query_agent.py        # RAG查询Agent（统一入口，新建）
    └── handler_agent.py          # 主控Agent（修改）
```

---

## 总结

本设计文档定义了RAG链路的完整实现方案，包括：

1. **架构设计**: HandlerAgent + RAGQueryAgent（统一查询入口）
2. **核心优势**: LLM自动判断返回格式，减少Agent数量，降低维护成本
3. **技术选型**: ChromaDB + text2vec + Claude
4. **数据流程**: 收集 → 向量化 → 存储 → 检索 → 生成
5. **实现计划**: 4个阶段，逐步推进

该设计独立于回测引擎，可以并行开发，互不影响。
