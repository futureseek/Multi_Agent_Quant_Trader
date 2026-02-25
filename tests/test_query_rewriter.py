#!/usr/bin/env python3
"""
查询改写功能测试脚本

测试LLM查询改写器的效果
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from service_layer.rag.query_rewriter import LLMQueryRewriter
from langchain_openai import ChatOpenAI


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_query_rewriter():
    """测试查询改写功能"""

    print_section("查询改写功能测试")

    # 初始化LLM
    print("🔧 初始化LLM...")
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # 或使用你的模型
        temperature=0
    )

    # 初始化查询改写器
    print("🔧 初始化查询改写器...")
    rewriter = LLMQueryRewriter(llm)

    # 测试用例
    test_cases = [
        "茅台",
        "招行",
        "低估值银行",
        "深圳的科技公司",
        "平安",
        "贵州茅台市盈率是多少",  # 完整查询，不应改写
    ]

    print_section("测试查询改写")

    results = []

    for i, query in enumerate(test_cases, 1):
        print(f"\n测试 {i}/{len(test_cases)}")
        print(f"原始查询: {query}")
        print("-" * 40)

        # 执行改写
        rewritten = rewriter.rewrite(query)

        if rewritten == query:
            print("✅ 查询已完整，无需改写")
        else:
            print(f"🔄 改写后: {rewritten}")

        results.append({
            "original": query,
            "rewritten": rewritten,
            "changed": rewritten != query
        })

    # 统计
    print_section("测试结果统计")

    changed_count = sum(1 for r in results if r["changed"])
    total_count = len(results)

    print(f"""
总测试用例: {total_count}
改写数量: {changed_count}
改写率: {changed_count / total_count * 100:.1f}%
    """)

    # 详细结果
    print("\n详细结果:")
    for i, r in enumerate(results, 1):
        status = "🔄 改写" if r["changed"] else "✅ 保持"
        print(f"{i}. [{status}] {r['original']}")
        if r["changed"]:
            print(f"   → {r['rewritten']}")

    # 统计信息
    print_section("改写器统计")

    stats = rewriter.get_stats()
    print(f"""
累计改写次数: {stats['rewrite_count']}
改写器类型: {stats['rewriter_type']}
    """)

    print("\n✅ 测试完成！")


if __name__ == "__main__":
    try:
        test_query_rewriter()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
