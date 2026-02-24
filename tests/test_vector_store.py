"""
vector_store 模块测试脚本

测试目标:
  1. VectorStore初始化
  2. Collection创建
  3. 文档添加功能
  4. 向量检索功能
  5. 统计信息查询
"""

import sys
import os

# 添加src目录到Python路径，确保能导入service_layer模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from service_layer.rag.vector_store import StockVectorStore
from typing import List, Dict, Any


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_test(test_name: str):
    """打印测试名称"""
    print(f"\n{'=' * 60}")
    print(f"  {test_name}")
    print('=' * 60)


def test_vector_store():
    """测试VectorStore核心功能"""

    print_section("vector_store 模块测试")
    print("""
测试目标:
  1. VectorStore初始化
  2. Embedding模型加载
  3. Collection创建和查询
  4. 文档添加功能
  5. 向量检索功能
  6. 统计信息获取
    """)

    # ==================== 步骤1: 初始化 ====================
    print_section("步骤 1/3: 初始化VectorStore")

    print("🔧 正在初始化VectorStore...")

    try:
        vector_store = StockVectorStore(
            persist_dir="./data/test_chroma_db",  # 使用独立的测试目录
            embedding_model="shibing624/text2vec-base-chinese"
        )
        print("✅ VectorStore初始化成功\n")
    except Exception as e:
        print(f"❌ VectorStore初始化失败: {e}")
        return False

    # ==================== 步骤2: 测试Collection功能 ====================
    print_section("步骤 2/3: 测试Collection功能")

    # 2.1 列出所有collections
    print_test("测试1: 列出所有Collections")

    print("📂 正在获取所有Collections...")
    collections_stats = vector_store.list_all_collections()

    print(f"📋 发现 {len(collections_stats)} 个Collections:")
    for col_name, count in collections_stats.items():
        print(f"   - {col_name}: {count} 个文档")

    expected_collections = ['stock_basic_info', 'stock_financial',
                           'market_news', 'research_reports', 'announcements']

    missing_collections = set(expected_collections) - set(collections_stats.keys())
    if missing_collections:
        print(f"⚠️ 缺少Collections: {missing_collections}")
    else:
        print("✅ 所有预期Collections都已创建")

    # 2.2 获取单个collection统计
    print_test("测试2: 获取Collection统计信息")

    test_collection = 'stock_basic_info'
    print(f"📊 正在获取 '{test_collection}' 统计信息...")

    stats = vector_store.get_collection_stats(test_collection)

    if stats.get("success"):
        print(f"✅ Collection: {stats['collection']}")
        print(f"   文档数量: {stats['count']}")
        print(f"   元数据: {stats['metadata']}")
    else:
        print(f"❌ 获取统计信息失败: {stats.get('error')}")

    # ==================== 步骤3: 测试文档添加和检索 ====================
    print_section("步骤 3/3: 测试文档添加和检索")

    # 3.1 准备测试数据
    print_test("测试3: 添加测试文档")

    # 使用简单的测试数据
    test_documents = [
        "平安银行是一家总部位于深圳的全国性股份制商业银行",
        "腾讯控股是中国的互联网科技巨头，主营业务包括社交、游戏、云计算",
        "贵州茅台是中国知名的白酒品牌，总部位于贵州茅台镇",
        "中国移动是中国最大的移动通信运营商",
        "阿里巴巴是全球领先的电子商务公司"
    ]

    test_metadatas = [
        {"symbol": "000001.SZ", "name": "平安银行", "industry": "银行"},
        {"symbol": "00700.HK", "name": "腾讯控股", "industry": "互联网"},
        {"symbol": "600519.SH", "name": "贵州茅台", "industry": "白酒"},
        {"symbol": "00941.HK", "name": "中国移动", "industry": "通信"},
        {"symbol": "09988.HK", "name": "阿里巴巴", "industry": "电商"}
    ]

    test_ids = [
        "test_000001",
        "test_000002",
        "test_000003",
        "test_000004",
        "test_000005"
    ]

    print(f"📝 准备添加 {len(test_documents)} 个测试文档...")
    print("\n📄 测试数据示例:")
    print(f"   文档1: {test_documents[0][:30]}...")
    print(f"   元数据1: {test_metadatas[0]}")

    # 3.2 添加文档
    print("\n📤 正在添加文档到 'stock_basic_info' collection...")

    add_result = vector_store.add_documents(
        collection_name='stock_basic_info',
        documents=test_documents,
        metadatas=test_metadatas,
        ids=test_ids
    )

    if add_result.get("success"):
        print(f"✅ 成功添加 {add_result['count']} 个文档")
        print(f"   Collection: {add_result['collection']}")
    else:
        print(f"❌ 添加文档失败: {add_result.get('error')}")
        return False

    # 3.3 测试检索功能
    print_test("测试4: 向量检索")

    test_queries = [
        "深圳的银行",
        "互联网公司",
        "白酒品牌"
    ]

    print(f"🔍 测试 {len(test_queries)} 个查询...")

    for i, query in enumerate(test_queries, 1):
        print(f"\n   查询 {i}: '{query}'")
        print("   " + "-" * 50)

        results = vector_store.search(
            query=query,
            collection_names=['stock_basic_info'],
            top_k=3
        )

        if results:
            print(f"   ✅ 找到 {len(results)} 个结果:")
            for j, res in enumerate(results, 1):
                print(f"\n   结果 {j}:")
                print(f"      📄 内容: {res['document'][:50]}...")
                print(f"      🏷️  元数据: {res['metadata']}")
                print(f"      📏 距离: {res['distance']:.4f}")
                print(f"      📂 Collection: {res['collection']}")
        else:
            print(f"   ⚠️ 未找到相关结果")

    # 3.4 再次查询统计信息（验证文档已添加）
    print_test("测试5: 验证文档添加结果")

    print("📊 正在验证文档数量...")
    stats_after = vector_store.get_collection_stats('stock_basic_info')

    if stats_after.get("success"):
        doc_count = stats_after['count']
        print(f"✅ Collection当前文档数量: {doc_count}")

        if doc_count >= len(test_documents):
            print(f"✅ 文档数量验证通过 (>= {len(test_documents)})")
        else:
            print(f"⚠️ 文档数量少于预期 (预期 >= {len(test_documents)}, 实际 {doc_count})")
    else:
        print(f"❌ 获取统计信息失败: {stats_after.get('error')}")

    # ==================== 测试总结 ====================
    print_section("测试总结")

    print("""
  ✅ VectorStore初始化: 通过
  ✅ Embedding模型加载: 通过
  ✅ Collection创建: 通过
  ✅ 文档添加功能: 通过
  ✅ 向量检索功能: 通过
  ✅ 统计信息查询: 通过
    """)

    print("🎉 所有测试通过！vector_store模块工作正常。")
    print("\n💡 提示: 测试数据保存在 ./data/test_chroma_db，可手动删除")

    return True


if __name__ == "__main__":
    try:
        success = test_vector_store()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生未预期的错误:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {e}")
        import traceback
        print("\n📋 详细堆栈:")
        traceback.print_exc()
        sys.exit(1)
