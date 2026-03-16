"""
RAG查询Agent - 统一处理选股和知识问答

通过向量检索 + LLM实现智能查询，自动判断返回格式
"""

from typing import Dict, Any, List, Optional
import json


class RAGQueryAgent:
    """RAG查询Agent - 统一处理选股和问答"""

    def __init__(self, vector_store, llm, enable_query_rewrite: bool = True):
        """
        初始化RAG查询Agent

        Args:
            vector_store: StockVectorStore实例
            llm: LLM实例（支持invoke方法）
            enable_query_rewrite: 是否启用查询改写（默认True）
        """
        self.vector_store = vector_store
        self.llm = llm
        self.enable_query_rewrite = enable_query_rewrite

        # 初始化查询改写器
        self.query_rewriter = None
        if enable_query_rewrite:
            try:
                from ..rag.query_rewriter import LLMQueryRewriter
                self.query_rewriter = LLMQueryRewriter(llm)
            except ImportError as e:
                print(f"⚠️ 查询改写模块导入失败: {e}")
                self.enable_query_rewrite = False

        print("✅ RAGQueryAgent初始化完成")

    def query(self, user_input: str, top_k: int = 10) -> Dict[str, Any]:
        """
        统一查询接口 - LLM自动判断返回格式

        Args:
            user_input: 用户问题（选股或问答）
            top_k: 返回结果数量

        Returns:
            {
                'success': True/False,
                'query_type': 'stock_selection' / 'knowledge_query',
                'result': {...},
                'sources': [...],
                'error': ... (失败时)
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔍 RAG查询: {user_input}")
            print(f"{'='*60}")

            # 0. 【新增】查询改写（如果启用）
            search_query = user_input
            if self.query_rewriter:
                search_query = self.query_rewriter.rewrite(user_input, enable=self.enable_query_rewrite)

            # 1. 向量检索（跨所有collection）
            search_results = self.vector_store.search(
                query=search_query,  # 使用改写后的查询
                collection_names=None,  # 全部collection
                top_k=top_k
            )

            if not search_results:
                return {
                    'success': False,
                    'error': '未找到相关信息，请尝试其他查询词'
                }

            print(f"📊 检索到 {len(search_results)} 个相关文档")

            # 2. 构建统一prompt（让LLM自动判断类型）
            prompt = self._build_unified_prompt(user_input, search_results, top_k)

            # 3. LLM生成响应
            print("🤖 LLM正在分析...")
            response = self.llm.invoke(prompt)

            # 4. 解析结果（自动识别JSON或自然语言）
            result = self._parse_response(response, search_results)

            if result['success']:
                print(f"✅ 查询成功，类型: {result['query_type']}")

            return result

        except Exception as e:
            print(f"❌ RAG查询失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _build_unified_prompt(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        top_k: int
    ) -> str:
        """
        构建统一prompt - LLM自动判断问题类型

        Args:
            question: 用户问题
            search_results: 检索结果列表
            top_k: 返回数量

        Returns:
            完整prompt字符串
        """
        # 构建上下文文本（限制前30个文档避免token超限）
        context_text = "\n\n".join([
            f"【参考文档{i+1}】\n{result['document']}"
            for i, result in enumerate(search_results[:30])
        ])

        template = """你是一个专业的智能投资助手。请根据以下参考文档回答用户问题。

参考文档:
{context}

用户问题: {question}

## 强制检查步骤（回答前必须执行）

步骤1：提取用户询问的公司/股票名称
- 从问题中提取具体的公司名或股票代码

步骤2：检查参考文档中是否包含该公司
- 逐一阅读参考文档，确认是否包含该公司名称
- 如果参考文档中完全没有该公司信息，停止回答，返回拒绝信息

步骤3：验证文档数量
- 如果参考文档少于5条，说明数据不足，告知用户

## 拒绝回答的标准格式

如果验证失败（不匹配或数据不足），返回：
```json
{{
    "query_type": "knowledge_query",
    "answer": "抱歉，知识库中没有找到关于[公司名]的相关信息。当前库中只有[实际有的公司名]的数据。"
}}
```

## 回答格式（仅当验证通过时）

选股类问题（找、筛选、推荐、哪些）：
```json
{{
    "query_type": "stock_selection",
    "stocks": [
        {{
            "symbol": "000001.SZ",
            "name": "平安银行",
            "reason": "市盈率5.2，符合条件"
        }}
    ]
}}
```

问答类问题（什么是、主营、介绍、公告、新闻）：
```json
{{
    "query_type": "knowledge_query",
    "answer": "基于文档的自然语言解答"
}}
```

严禁编造信息。如果文档中没有用户询问的公司，必须拒绝回答。
"""

        return template.format(
            context=context_text,
            question=question,
            top_k=top_k
        )

    def _parse_response(
        self,
        response,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        解析LLM响应

        Args:
            response: LLM响应对象
            search_results: 检索结果（用于返回来源）

        Returns:
            解析后的结果字典
        """
        try:
            # 提取内容
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取JSON（处理可能的markdown代码块）
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            # 解析JSON
            result = json.loads(json_str)

            # 构建来源信息
            sources = [
                f"{result['document'][:100]}..."
                for result in search_results[:5]
            ]

            return {
                'success': True,
                'query_type': result.get('query_type'),
                'result': result,
                'sources': sources
            }

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败，降级为文本模式: {e}")

            # 降级：如果JSON解析失败，返回原始文本
            content = response.content if hasattr(response, 'content') else str(response)

            return {
                'success': True,
                'query_type': 'knowledge_query',
                'result': {'answer': content},
                'sources': [f"{r['document'][:100]}..." for r in search_results[:3]]
            }

        except Exception as e:
            print(f"❌ 解析响应失败: {e}")
            return {
                'success': False,
                'error': f'解析响应失败: {str(e)}'
            }

    def format_result_for_display(self, query_result: Dict[str, Any], user_input: str) -> str:
        """
        格式化查询结果用于显示

        Args:
            query_result: query()方法返回的结果
            user_input: 原始用户输入

        Returns:
            格式化的Markdown文本
        """
        if not query_result.get('success'):
            return f"❌ 查询失败: {query_result.get('error', '未知错误')}"

        query_type = query_result.get('query_type')
        result_data = query_result.get('result', {})
        sources = query_result.get('sources', [])

        if query_type == 'stock_selection':
            # 选股结果格式化
            stocks = result_data.get('stocks', [])

            response_text = f"## 📊 选股结果\n\n"
            response_text += f"**筛选条件**: {user_input}\n\n"

            if not stocks:
                response_text += "未找到符合条件的股票。\n"
            else:
                for i, stock in enumerate(stocks[:10], 1):
                    response_text += f"{i}. **{stock.get('symbol')}** - {stock.get('name')}\n"
                    response_text += f"   - {stock.get('reason', '')}\n"

            # 添加来源说明
            if sources:
                response_text += f"\n*基于知识库中 {len(sources)} 个相关文档分析*"

            return response_text

        elif query_type == 'knowledge_query':
            # 问答结果格式化
            answer = result_data.get('answer', '')

            response_text = f"## 📖 知识库查询结果\n\n"
            response_text += f"{answer}\n"

            # 添加来源
            if sources:
                response_text += f"\n**参考来源：**\n"
                for i, source in enumerate(sources[:3], 1):
                    response_text += f"{i}. {source}\n"

            return response_text

        else:
            return f"❌ 未知的查询类型: {query_type}"
