"""
工具调用测试脚本

独立测试三个数据工具是否能正常调用
"""

import asyncio
import sys
import os

# 添加项目路径 - 向上4级回到项目根目录，再加一级到 src
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from src.service_layer.tools.daily_data_tool import DailyDataTool
from src.service_layer.tools.adj_factor import get_adj_factor
from src.service_layer.tools.daily_basic import get_daily_basic


async def test_daily_stock_data():
    """测试日K线数据获取工具"""
    print("=" * 60)
    print("测试1: 日K线数据获取工具 (get_daily_stock_data)")
    print("=" * 60)

    tool = DailyDataTool()

    try:
        # 测试用例1：指定股票代码和日期
        print("\n测试1.1: 获取贵州茅台日K线数据 (2020-2024)")
        result1 = tool.get_daily_data(
            ts_code="600519.SH",
            start_date="20200101",
            end_date="20241231"
        )

        print(f"✅ 测试1.1成功")
        print(f"   返回类型: {type(result1)}")
        print(f"   success: {result1.get('success', False)}")
        print(f"   数据条数: {result1.get('count', 0)}")

        if result1.get("success"):
            data = result1.get("data", {})
            if "data" in data and isinstance(data["data"], dict):
                print(f"   data字段键: {list(data['data'].keys())}")

        # 测试用例2：只指定股票代码（获取最近数据）
        print("\n测试1.2: 获取招商银行最近数据")
        result2 = tool.get_daily_data(ts_code="600036.SH")

        print(f"✅ 测试1.2成功")
        print(f"   success: {result2.get('success', False)}")
        print(f"   数据条数: {result2.get('count', 0)}")

        print("\n✅ 测试1通过！\n")

    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()


async def test_adj_factor():
    """测试复权因子获取工具"""
    print("\n" + "=" * 60)
    print("测试2: 复权因子获取工具 (get_adj_factor)")
    print("=" * 60)

    tool = AdjFactorTool()

    try:
        # 测试：获取复权因子
        print("\n测试2.1: 获取贵州茅台复权因子")
        result1 = tool.get_adj_factor(
            ts_code="600519.SH",
            start_date="20200101",
            end_date="20241231"
        )

        print(f"✅ 测试2.1成功")
        print(f"   返回类型: {type(result1)}")
        print(f"   success: {result1.get('success', False)}")
        print(f"   数据条数: {result1.get('count', 0)}")

        if result1.get("success"):
            data = result1.get("data", {})
            print(f"   数据字段: {list(data.keys())}")

        print("\n✅ 测试2通过！\n")

    except Exception as e:
        print(f"\n❌ 测试2失败: {e}")
        import traceback
        traceback.print_exc()


async def test_daily_basic():
    """测试日指标数据获取工具"""
    print("\n" + "=" * 60)
    print("测试3: 日指标数据获取工具 (get_daily_basic)")
    print("=" * 60)

    tool = DailyBasicTool()

    try:
        # 测试：获取日指标数据
        print("\n测试3.1: 获取贵州茅台日指标数据")
        result1 = tool.get_daily_basic(
            ts_code="600519.SH",
            start_date="20200101",
            end_date="20241231"
        )

        print(f"✅ 测试3.1成功")
        print(f"   返回类型: {type(result1)}")
        print(f"   success: {result1.get('success', False)}")
        print(f"   数据条数: {result1.get('count', 0)}")

        if result1.get("success"):
            data = result1.get("data", {})
            print(f"   数据字段: {list(data.keys())}")

        print("\n✅ 测试3通过！\n")

    except Exception as e:
        print(f"\n❌ 测试3失败: {e}")
        import traceback
        traceback.print_exc()


async def run_all_tests():
    """运行所有工具测试"""
    print("\n" + "=" * 60)
    print("独立工具调用测试")
    print("=" * 60)

    try:
        await test_daily_stock_data()
        await test_adj_factor()
        await test_daily_basic()

        print("\n" + "=" * 60)
        print("✅ 所有工具测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
