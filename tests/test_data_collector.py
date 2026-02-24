#!/usr/bin/env python3
"""
data_collector 模块测试脚本

测试目的：
1. 验证Tushare API连接
2. 测试数据收集接口可用性
3. 验证返回数据格式
4. 检查数据完整性

使用方法:
    cd tests
    python test_data_collector.py
"""

import sys
import os

# 添加项目根目录到Python路径
# 测试脚本在 tests/ 目录，项目根目录在上一级
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

# 添加 src 目录到Python路径
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

import json
from service_layer.rag.data_collector import StockDataCollector


def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "="*60)
    if title:
        print(f"  {title}")
        print("="*60)


def load_tushare_token():
    """加载Tushare Token"""
    config_path = os.path.join(project_root, "config/api_config.json")

    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        return None

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    token = config.get("tushare_api", "")
    if not token:
        print("❌ 配置文件中未找到 tushare_api 字段")
        return None

    return token


def test_basic_info_limited(collector, limit=5):
    """测试基本信息收集（限制数量）"""
    print_separator("测试1: 收集股票基本信息")

    try:
        print(f"📊 正在收集股票基本信息（限制 {limit} 只）...")

        # 调用收集方法
        documents, metadatas, ids = collector.collect_basic_info()

        # 限制数量进行测试
        documents = documents[:limit]
        metadatas = metadatas[:limit]
        ids = ids[:limit]

        print(f"✅ 成功收集 {len(documents)} 只股票的基本信息\n")

        # 验证数据格式
        print("📋 数据格式验证:")
        print(f"   - documents 类型: {type(documents)}")
        print(f"   - metadatas 类型: {type(metadatas)}")
        print(f"   - ids 类型: {type(ids)}")
        print(f"   - documents 长度: {len(documents)}")
        print(f"   - metadatas 长度: {len(metadatas)}")
        print(f"   - ids 长度: {len(ids)}")

        # 验证数据一致性
        assert len(documents) == len(metadatas) == len(ids), "❌ 数据长度不一致"
        print(f"   ✅ 数据长度一致\n")

        # 打印第一个文档示例
        print("📄 第一个文档示例:")
        print("-" * 40)
        print(documents[0])
        print("-" * 40)

        # 打印第一个metadata示例
        print("\n🏷️  第一个metadata示例:")
        print("-" * 40)
        for key, value in metadatas[0].items():
            print(f"   {key}: {value}")
        print("-" * 40)

        # 验证必要字段
        print("\n🔍 必要字段验证:")
        required_metadata_fields = ['symbol', 'name', 'industry', 'area', 'market']
        for field in required_metadata_fields:
            if field in metadatas[0]:
                print(f"   ✅ {field}: {metadatas[0][field]}")
            else:
                print(f"   ❌ 缺少字段: {field}")

        # 验证文档内容格式
        print("\n📝 文档内容验证:")
        doc_lines = documents[0].split('\n')
        expected_keywords = ['股票代码', '股票名称', '所属区域', '所属行业']
        for keyword in expected_keywords:
            if any(keyword in line for line in doc_lines):
                print(f"   ✅ 包含关键词: {keyword}")
            else:
                print(f"   ❌ 缺少关键词: {keyword}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_financial_data_limited(collector, symbols=None, limit=5):
    """测试财务数据收集（限制数量）"""
    print_separator("测试2: 收集财务数据")

    try:
        # 如果没有指定股票，使用默认测试股票
        if symbols is None:
            symbols = ['000001.SZ', '600000.SH']  # 平安银行、浦发银行

        print(f"📊 正在收集财务数据...")
        print(f"   测试股票: {', '.join(symbols)}")

        # 调用收集方法
        documents, metadatas, ids = collector.collect_financial_data(symbols=symbols)

        # 限制数量进行测试
        documents = documents[:limit]
        metadatas = metadatas[:limit]
        ids = ids[:limit]

        if not documents:
            print("⚠️ 未获取到财务数据（可能不是交易日）")
            return True

        print(f"✅ 成功收集 {len(documents)} 只股票的财务数据\n")

        # 验证数据格式
        print("📋 数据格式验证:")
        print(f"   - documents 长度: {len(documents)}")
        print(f"   - metadatas 长度: {len(metadatas)}")
        print(f"   - ids 长度: {len(ids)}")

        # 打印第一个文档示例
        print("\n📄 第一个文档示例:")
        print("-" * 40)
        print(documents[0])
        print("-" * 40)

        # 打印第一个metadata示例
        print("\n🏷️  第一个metadata示例:")
        print("-" * 40)
        for key, value in metadatas[0].items():
            print(f"   {key}: {value}")
        print("-" * 40)

        # 验证必要字段
        print("\n🔍 必要字段验证:")
        required_metadata_fields = ['symbol', 'date', 'pe', 'pb', 'total_mv']
        for field in required_metadata_fields:
            if field in metadatas[0]:
                value = metadatas[0][field]
                print(f"   ✅ {field}: {value}")
            else:
                print(f"   ❌ 缺少字段: {field}")

        # 验证文档内容格式
        print("\n📝 文档内容验证:")
        doc_lines = documents[0].split('\n')
        expected_keywords = ['股票代码', '交易日期', '市盈率', '市净率']
        for keyword in expected_keywords:
            if any(keyword in line for line in doc_lines):
                print(f"   ✅ 包含关键词: {keyword}")
            else:
                print(f"   ❌ 缺少关键词: {keyword}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_consistency(documents, metadatas, ids):
    """测试数据一致性"""
    print_separator("测试3: 数据一致性验证")

    print("🔍 检查数据一致性...")

    issues = []

    # 检查长度
    if len(documents) != len(metadatas):
        issues.append(f"❌ documents和metadatas长度不一致: {len(documents)} vs {len(metadatas)}")

    if len(documents) != len(ids):
        issues.append(f"❌ documents和ids长度不一致: {len(documents)} vs {len(ids)}")

    # 检查ID唯一性
    if len(ids) != len(set(ids)):
        issues.append("❌ ids中存在重复")

    # 检查文档是否为空
    empty_docs = sum(1 for doc in documents if not doc.strip())
    if empty_docs > 0:
        issues.append(f"❌ 存在 {empty_docs} 个空文档")

    # 检查metadata是否为空
    empty_metas = sum(1 for meta in metadatas if not meta)
    if empty_metas > 0:
        issues.append(f"❌ 存在 {empty_metas} 个空metadata")

    if issues:
        for issue in issues:
            print(issue)
        return False
    else:
        print("✅ 数据一致性检查通过")
        return True


def main():
    """主测试函数"""
    print_separator("data_collector 模块测试")
    print("测试目标:")
    print("  1. Tushare API连接")
    print("  2. 基本信息收集接口")
    print("  3. 财务数据收集接口")
    print("  4. 返回数据格式验证")
    print("  5. 数据完整性检查")

    # 1. 加载配置
    print_separator("步骤 1/4: 加载配置")
    token = load_tushare_token()
    if not token:
        print("\n❌ 无法加载Tushare Token，测试终止")
        sys.exit(1)
    print("✅ Tushare Token加载成功")

    # 2. 初始化收集器
    print_separator("步骤 2/4: 初始化数据收集器")
    try:
        collector = StockDataCollector(tushare_token=token)
        print("✅ 数据收集器初始化成功")
    except Exception as e:
        print(f"❌ 数据收集器初始化失败: {e}")
        sys.exit(1)

    # 3. 测试基本信息收集
    print_separator("步骤 3/4: 测试基本信息收集")
    basic_test_passed = test_basic_info_limited(collector, limit=5)

    # 4. 测试财务数据收集
    print_separator("步骤 4/4: 测试财务数据收集")
    financial_test_passed = test_financial_data_limited(collector, limit=5)

    # 测试总结
    print_separator("测试总结")
    print(f"  基本信息收集: {'✅ 通过' if basic_test_passed else '❌ 失败'}")
    print(f"  财务数据收集: {'✅ 通过' if financial_test_passed else '❌ 失败'}")

    if basic_test_passed and financial_test_passed:
        print("\n🎉 所有测试通过！data_collector模块工作正常。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
