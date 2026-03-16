"""
BGE Reranker 重排序模块

使用BGE交叉编码器对检索结果进行重排序，提升RAG准确率
"""

import os
from typing import List, Dict, Any

# 设置HuggingFace镜像源（解决国内网络访问问题）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'


class BGEReranker:
    """BGE重排序模型"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        """
        初始化BGE Reranker

        Args:
            model_name: 模型名称，默认使用bge-reranker-v2-m3
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """延迟加载模型（避免启动时加载失败）"""
        if self.model is not None:
            return

        try:
            print(f"📦 加载BGE Reranker模型: {self.model_name}")
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(self.model_name)
            print("✅ BGE Reranker模型加载完成")

        except Exception as e:
            print(f"❌ BGE Reranker模型加载失败: {e}")
            print("⚠️ 将跳过重排序功能")
            self.model = None

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序

        Args:
            query: 用户查询
            documents: 检索结果列表，格式：[{"document": str, "metadata": dict, "distance": float}, ...]
            top_k: 返回的文档数量

        Returns:
            重排序后的文档列表
        """
        # 如果模型未加载，返回原结果
        if self.model is None:
            print("⚠️ Reranker模型未加载，跳过重排序")
            return documents[:top_k]

        if not documents:
            return []

        try:
            print(f"🔄 对{len(documents)}个文档进行重排序...")

            # 1. 构造(query, document)对
            pairs = [(query, doc["document"]) for doc in documents]

            # 2. 批量打分
            scores = self.model.predict(pairs)

            # 3. 按分数排序
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # 4. 返回top_k
            reranked_docs = [doc for doc, score in scored_docs[:top_k]]

            # 5. 打印重排序效果
            if len(reranked_docs) > 0:
                print(f"✅ 重排序完成，Top-{min(3, len(reranked_docs))}结果:")
                for i, (doc, score) in enumerate(scored_docs[:3], 1):
                    doc_preview = doc["document"][:50] + "..."
                    print(f"  {i}. [{score:.2f}] {doc_preview}")

            return reranked_docs

        except Exception as e:
            print(f"❌ 重排序失败: {e}")
            return documents[:top_k]

    def is_available(self) -> bool:
        """
        检查模型是否可用

        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None
