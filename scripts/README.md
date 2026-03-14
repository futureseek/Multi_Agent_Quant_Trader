# Scripts 目录说明

本目录包含数据初始化和新闻更新的核心脚本。

---

## 1. init_rag_db.py - RAG向量库初始化

**用途**：构建股票基本信息和财务指标的向量数据库

### 使用方法

```bash
# 确保配置文件存在
cd /home/ligenghao/Multi_Agent_Quant_Trader
ls config/api_config.json

# 运行初始化脚本
python scripts/init_rag_db.py
```

### 功能说明

- 从Tushare获取股票基本信息（公司名、行业、上市日期等）
- 从Tushare获取财务指标（PE、PB、ROE等）
- 向量化后存储到ChromaDB的 `stock_basic_info` 和 `stock_financial` collection

### 首次使用

如果提示清空数据，选择：
- `yes` - 全量重建（首次使用选这个）
- `no` - 保留现有数据，增量添加

### 更新频率

建议：**每月更新一次**（财务数据按季发布）

---

## 2. crawl_news.py - 新闻爬虫

**用途**：爬取东方财富网公告并自动向量化到ChromaDB

### 使用方法

```bash
# 基础使用（爬取500条 + 向量化）
python scripts/crawl_news.py

# 自定义数量
python scripts/crawl_news.py 1000

# 仅爬取不向量化
python scripts/crawl_news.py 500 --no-vectorize

# 向量化已有数据
python scripts/crawl_news.py --vectorize-only

# 查看帮助
python scripts/crawl_news.py --help
```

### 工作流程

```
爬取公告 → 提取股票代码 → 增量去重 → 保存JSON → 向量化到ChromaDB
```

### 数据存储

- **JSON文件**：`data/news_sample.json`
- **向量库**：ChromaDB的 `market_news` collection

### 更新频率

建议：**每天运行一次**（定时任务）

```bash
# crontab示例：每天凌晨2点更新
0 2 * * * cd /home/ligenghao/Multi_Agent_Quant_Trader && python scripts/crawl_news.py 500 >> logs/crawl.log 2>&1
```

---

## 3. build_stock_map.py - 股票映射表生成

**用途**：生成公司名到股票代码的映射表

### 使用方法

```bash
python scripts/build_stock_map.py
```

### 功能说明

- 从Tushare获取全部A股列表（5489只股票）
- 生成映射表：`{"平安银行": "000001.SZ", "万科A": "000002.SZ", ...}`
- 保存到：`data/company_stock_map.json`

### 何时使用

1. **首次使用**：映射表文件不存在时
2. **更新映射表**：新股票上市后

### 注意事项

- 需要Tushare API Token（配置在 `config/api_config.json`）
- 正常情况下**无需重复运行**（映射表已存在）

---

## 数据文件结构

```
data/
├── chroma_db/              # ChromaDB向量库
│   ├── stock_basic_info/   # 股票基本信息（init_rag_db.py生成）
│   ├── stock_financial/    # 财务指标（init_rag_db.py生成）
│   └── market_news/        # 新闻公告（crawl_news.py生成）
├── news_sample.json        # 新闻JSON数据（crawl_news.py生成）
└── company_stock_map.json  # 股票映射表（build_stock_map.py生成）
```

---

## 完整初始化流程

### 首次部署

```bash
# 1. 生成股票映射表
python scripts/build_stock_map.py

# 2. 初始化RAG向量库
python scripts/init_rag_db.py

# 3. 爬取新闻
python scripts/crawl_news.py 500
```

### 日常维护

```bash
# 每天爬取新闻（自动化）
python scripts/crawl_news.py 500

# 每月更新财务数据（手动）
python scripts/init_rag_db.py

# 需要时更新股票映射表
python scripts/build_stock_map.py
```

---

## 依赖说明

所有脚本依赖项目根目录的配置：

- `config/api_config.json` - Tushare API Token和模型配置

确保配置文件存在后运行脚本。
