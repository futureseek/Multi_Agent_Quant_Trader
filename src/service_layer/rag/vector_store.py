"""
向量存储模块 - 基于ChromaDB

提供股票知识向量化存储和检索功能
"""

import os

# 设置HuggingFace镜像源（解决国内网络访问问题）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional


class StockVectorStore:
    """股票知识向量存储"""

    def __init__(
        self,
        persist_dir: str = "./data/chroma_db",
        embedding_model: str = "shibing624/text2vec-base-chinese"
    ):
        """
        初始化向量存储

        Args:
            persist_dir: ChromaDB持久化目录
            embedding_model: Embedding模型名称
        """
        # 确保持久化目录存在
        os.makedirs(persist_dir, exist_ok=True)

        # 初始化ChromaDB客户端（新版API）
        self.client = chromadb.PersistentClient(path=persist_dir)

        # 初始化Embedding模型
        print(f"📦 加载Embedding模型: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        print("✅ Embedding模型加载完成")

        # 初始化Reranker（直接启用）
        try:
            from .reranker import BGEReranker
            self.reranker = BGEReranker()
            self.enable_reranker = self.reranker.is_available()
        except Exception as e:
            print(f"⚠️ Reranker初始化失败: {e}")
            self.reranker = None
            self.enable_reranker = False

        # 创建多个collection（分类存储）
        self.collections = {}
        collection_names = [
            'stock_basic_info',    # 股票基本信息
            'stock_financial',      # 财务指标
            'market_news',          # 市场新闻（预留）
            'research_reports',     # 研究报告（预留）
            'announcements'         # 公告信息（预留）
        ]

        for name in collection_names:
            self.collections[name] = self._create_collection(name)

        print(f"✅ 向量存储初始化完成，Collections: {list(self.collections.keys())}")

    def _create_collection(self, name: str):
        """
        创建collection

        Args:
            name: collection名称

        Returns:
            ChromaDB collection对象
        """
        # 检查collection是否已存在
        existing_collections = [col.name for col in self.client.list_collections()]

        if name in existing_collections:
            print(f"📂 Collection已存在: {name}")
            return self.client.get_collection(name)
        else:
            print(f"🆕 创建新Collection: {name}")
            return self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # 余弦相似度
            )

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> Dict[str, Any]:
        """
        批量添加文档到指定collection

        Args:
            collection_name: collection名称
            documents: 文档内容列表
            metadatas: 元数据列表
            ids: 文档ID列表

        Returns:
            操作结果
        """
        if collection_name not in self.collections:
            return {
                "success": False,
                "error": f"Collection '{collection_name}' 不存在"
            }

        try:
            # 生成embeddings
            print(f"🔄 正在向量化 {len(documents)} 个文档...")
            embeddings = self.embedder.encode(documents).tolist()

            # 添加到collection
            self.collections[collection_name].add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            print(f"✅ 成功添加 {len(documents)} 个文档到 '{collection_name}'")

            return {
                "success": True,
                "collection": collection_name,
                "count": len(documents)
            }

        except Exception as e:
            print(f"❌ 添加文档失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def search(
        self,
        query: str,
        collection_names: Optional[List[str]] = None,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        跨collection检索（集成Reranker重排序）

        Args:
            query: 查询文本
            collection_names: 指定检索的collection列表，None表示全部
            top_k: 返回的结果数
            filter_metadata: 元数据过滤条件

        Returns:
            检索结果列表，格式：[{"document": str, "metadata": dict, "distance": float}, ...]
        """
        if collection_names is None:
            collection_names = list(self.collections.keys())

        # 生成查询向量
        query_embedding = self.embedder.encode([query]).tolist()

        all_results = []

        for name in collection_names:
            if name not in self.collections:
                continue

            try:
                # 查询collection（召回更多候选，为重排序做准备）
                # 设定召回上限，避免过度召回
                if self.enable_reranker:
                    recall_k = min(top_k * 3, 50)  # 最多召回50个/collection
                else:
                    recall_k = top_k

                results = self.collections[name].query(
                    query_embeddings=query_embedding,
                    n_results=recall_k,
                    where=filter_metadata
                )

                # 解析结果
                if results['documents'] and len(results['documents']) > 0:
                    for i, doc in enumerate(results['documents'][0]):
                        all_results.append({
                            "document": doc,
                            "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                            "distance": results['distances'][0][i] if 'distances' in results else 0.0,
                            "collection": name
                        })

            except Exception as e:
                print(f"⚠️ 从 '{name}' 检索失败: {e}")
                continue

        # 按距离排序（升序）
        all_results.sort(key=lambda x: x["distance"])

        print(f"🔍 向量检索完成，召回 {len(all_results)} 个候选")

        # Reranker重排序
        if self.enable_reranker and self.reranker and len(all_results) > 0:
            all_results = self.reranker.rerank(query, all_results, top_k)

        return all_results[:top_k]

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        获取collection统计信息

        Args:
            collection_name: collection名称

        Returns:
            统计信息
        """
        if collection_name not in self.collections:
            return {
                "success": False,
                "error": f"Collection '{collection_name}' 不存在"
            }

        try:
            collection = self.collections[collection_name]
            count = collection.count()

            return {
                "success": True,
                "collection": collection_name,
                "count": count,
                "metadata": collection.metadata
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def list_all_collections(self) -> Dict[str, int]:
        """
        列出所有collection及其文档数量

        Returns:
            {collection_name: count}
        """
        stats = {}
        for name, collection in self.collections.items():
            try:
                stats[name] = collection.count()
            except:
                stats[name] = 0
        return stats

    def clear_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        清空指定collection

        Args:
            collection_name: collection名称

        Returns:
            操作结果
        """
        if collection_name not in self.collections:
            return {
                "success": False,
                "error": f"Collection '{collection_name}' 不存在"
            }

        try:
            # 删除并重新创建collection
            self.client.delete_collection(collection_name)
            self.collections[collection_name] = self._create_collection(collection_name)

            print(f"🗑️ 已清空Collection: {collection_name}")

            return {
                "success": True,
                "collection": collection_name
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
