#!/usr/bin/env python3
"""
RAG数据验证脚本

验证向量库中的数据内容和查询功能
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from service_layer.rag.vector_store import StockVectorStore


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    print_section("RAG数据验证")

    # 初始化向量存储（使用项目根目录的统一路径）
    print("📂 正在连接向量数据库...")

    # 获取项目根目录（从tests/向上一级）
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    persist_dir = os.path.join(project_root, 'data', 'chroma_db')

    print(f"📂 数据路径: {persist_dir}")
    vector_store = StockVectorStore(persist_dir=persist_dir)

    # 1. 显示collection统计
    print_section("1. Collection统计")

    stats = vector_store.list_all_collections()
    print(f"📊 发现 {len(stats)} 个Collections:")
    for name, count in stats.items():
        status = "✅" if count > 0 else "⚠️ 空"
        print(f"   {status} {name}: {count} 个文档")

    # 2. 查询基本信息
    print_section("2. 查询股票基本信息")

    test_queries_basic = [
        "深圳的银行股",
        "科技股",
        "白酒行业"
    ]

    for query in test_queries_basic:
        print(f"\n🔍 查询: '{query}'")
        print("-" * 50)

        results = vector_store.search(
            query=query,
            collection_names=['stock_basic_info'],
            top_k=2
        )

        if results:
            for i, res in enumerate(results, 1):
                print(f"\n结果 {i}:")
                print(f"   📄 {res['document'][:100]}...")
                print(f"   🏷️  {res['metadata']}")
                print(f"   📏 相似度: {1 - res['distance']:.2%}")  # 转换为相似度
        else:
            print("   ⚠️ 未找到结果")

    # 3. 查询财务数据
    print_section("3. 查询财务数据")

    test_queries_financial = [
        "市盈率低的银行股",
        "市值大的公司",
        "高股息率股票"
    ]

    for query in test_queries_financial:
        print(f"\n🔍 查询: '{query}'")
        print("-" * 50)

        results = vector_store.search(
            query=query,
            collection_names=['stock_financial'],
            top_k=2
        )

        if results:
            for i, res in enumerate(results, 1):
                print(f"\n结果 {i}:")
                # 完整显示财务数据
                lines = res['document'].split('\n')
                for line in lines[:5]:  # 只显示前5行
                    print(f"   {line}")
                print(f"   🏷️  {res['metadata']}")
                print(f"   📏 相似度: {1 - res['distance']:.2%}")
        else:
            print("   ⚠️ 未找到结果")

    # 4. 跨collection检索
    print_section("4. 跨Collection检索（同时搜索基本信息+财务数据）")

    query = "平安银行的基本情况和财务指标"
    print(f"🔍 查询: '{query}'")
    print("-" * 50)

    results = vector_store.search(
        query=query,
        collection_names=['stock_basic_info', 'stock_financial'],
        top_k=5
    )

    if results:
        for i, res in enumerate(results, 1):
            collection_type = "基本信息" if res['collection'] == 'stock_basic_info' else "财务数据"
            print(f"\n结果 {i} [{collection_type}]:")
            print(f"   📄 {res['document'][:80]}...")
            print(f"   🏷️  {res['metadata']}")
            print(f"   📏 相似度: {1 - res['distance']:.2%}")
    else:
        print("   ⚠️ 未找到结果")

    # 5. 验证总结
    print_section("验证总结")

    total_docs = sum(stats.values())
    print(f"""
📊 数据统计:
   - 总文档数: {total_docs}
   - 基本信息: {stats.get('stock_basic_info', 0)} 个
   - 财务数据: {stats.get('stock_financial', 0)} 个

✅ 向量化: {'正常' if total_docs > 0 else '❌ 无数据'}
✅ 检索功能: {'正常' if total_docs > 0 else '❌ 无法测试'}
✅ 语义匹配: {'正常' if total_docs > 0 else '❌ 无法测试'}
    """)

    if total_docs > 0:
        print("🎉 RAG数据验证通过！可以开始使用RAG查询功能了。")
    else:
        print("⚠️ 向量库为空，请先运行 init_rag_db.py 初始化数据")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 验证被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
