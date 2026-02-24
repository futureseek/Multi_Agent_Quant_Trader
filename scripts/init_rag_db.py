#!/usr/bin/env python3
"""
RAG向量数据库初始化脚本

用于构建股票知识向量库，包括：
- 股票基本信息
- 财务指标数据

使用方法:
    cd src/service_layer
    python ../../scripts/init_rag_db.py
"""

import sys
import os

# 获取脚本所在目录（scripts/）
script_dir = os.path.dirname(os.path.abspath(__file__))
# 添加src目录到Python路径（scripts的父目录）
sys.path.insert(0, os.path.join(script_dir, '..', 'src'))

# 定义项目根目录（用于配置文件路径）
project_root = os.path.join(script_dir, '..')

import json
from service_layer.rag.vector_store import StockVectorStore
from service_layer.rag.data_collector import StockDataCollector


def load_config():
    """加载配置文件"""
    config_path = os.path.join(project_root, "config/api_config.json")

    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        print("请确保 config/api_config.json 文件存在并包含 tushare_api 字段")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    tushare_token = config.get("tushare_api", "")

    if not tushare_token:
        print("❌ 配置文件中未找到 tushare_api 字段")
        sys.exit(1)

    return tushare_token


def main():
    """主函数"""
    print("="*60)
    print("RAG向量数据库初始化脚本")
    print("="*60)
    print()

    # 1. 加载配置
    print("步骤 1/4: 加载配置...")
    tushare_token = load_config()
    print("✅ 配置加载完成")
    print()

    # 2. 初始化向量存储
    print("步骤 2/4: 初始化向量存储...")

    # 使用项目根目录的统一路径
    persist_dir = os.path.join(project_root, 'data', 'chroma_db')
    print(f"📂 数据保存路径: {persist_dir}")

    vector_store = StockVectorStore(persist_dir=persist_dir)

    # 显示现有collection统计
    stats = vector_store.list_all_collections()
    if stats and sum(stats.values()) > 0:
        print("📊 现有Collection统计:")
        for name, count in stats.items():
            print(f"   - {name}: {count} 个文档")

        # 询问是否清空
        response = input("\n是否清空现有数据并重新构建？(yes/no): ").strip().lower()
        if response == 'yes':
            print("🗑️ 清空现有数据...")
            vector_store.clear_collection('stock_basic_info')
            vector_store.clear_collection('stock_financial')
        else:
            print("保留现有数据，继续添加...")

    print()

    # 3. 初始化数据收集器
    print("步骤 3/4: 初始化数据收集器...")
    data_collector = StockDataCollector(tushare_token=tushare_token)
    print()

    # 4. 收集数据并构建向量库
    print("步骤 4/4: 收集数据并构建向量库...")
    print()

    results = data_collector.collect_and_build_knowledge_base(
        vector_store=vector_store,
        collect_basic=True,
        collect_financial=True
    )

    print()
    print("="*60)
    print("初始化完成！")
    print("="*60)

    # 显示结果摘要
    print("\n📊 构建结果摘要:")

    if results.get("basic_info"):
        basic = results["basic_info"]
        if basic["success"]:
            print(f"✅ 基本信息: {basic['count']} 个文档")
        else:
            print(f"❌ 基本信息: {basic.get('error', '失败')}")

    if results.get("financial"):
        financial = results["financial"]
        if financial["success"]:
            print(f"✅ 财务数据: {financial['count']} 个文档")
        else:
            print(f"❌ 财务数据: {financial.get('error', '失败')}")

    # 显示最终统计
    print("\n📊 最终Collection统计:")
    final_stats = vector_store.list_all_collections()
    for name, count in final_stats.items():
        print(f"   - {name}: {count} 个文档")

    print()
    print("✅ RAG向量数据库构建完成！现在可以使用RAG查询功能了。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
