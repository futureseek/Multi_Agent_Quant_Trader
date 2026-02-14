"""
StrategyAgent单元测试
"""

import asyncio
import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.service_layer.agents.strategy_agent import StrategyAgent


async def test_strategy_generation():
    """测试策略生成"""
    print("=" * 60)
    print("测试1: 策略生成")
    print("=" * 60)

    agent = StrategyAgent()

    # 测试1：简单请求
    print("\n测试1.1: 生成双均线策略")
    result1 = await agent.generate_strategy(
        user_request="生成一个双均线策略"
    )

    assert result1["success"] == True, "策略生成应该成功"
    assert "strategy_code" in result1, "结果应该包含strategy_code"
    assert "class " in result1["strategy_code"], "代码应该包含class定义"
    print(f"✅ 测试1.1通过 - 策略类名: {result1.get('strategy_name', 'N/A')}")

    # 测试2：带数据上下文的请求
    print("\n测试1.2: 生成带数据上下文的策略")
    result2 = await agent.generate_strategy(
        user_request="为茅台设计均线策略",
        data_context={
            "stock_info": {"code": "600519.SH", "name": "贵州茅台"},
            "date_range": ("20230101", "20241231")
        }
    )

    assert result2["success"] == True, "策略生成应该成功"
    print(f"✅ 测试1.2通过 - 策略类名: {result2.get('strategy_name', 'N/A')}")

    # 测试3：RSI策略
    print("\n测试1.3: 生成RSI策略")
    result3 = await agent.generate_strategy(
        user_request="生成一个RSI超买超卖策略"
    )

    assert result3["success"] == True, "策略生成应该成功"
    print(f"✅ 测试1.3通过 - 策略类名: {result3.get('strategy_name', 'N/A')}")

    # 测试4：MACD策略
    print("\n测试1.4: 生成MACD策略")
    result4 = await agent.generate_strategy(
        user_request="生成一个MACD金叉死叉策略"
    )

    assert result4["success"] == True, "策略生成应该成功"
    print(f"✅ 测试1.4通过 - 策略类名: {result4.get('strategy_name', 'N/A')}")

    print("\n" + "=" * 60)
    print("✅ 所有策略生成测试通过！")
    print("=" * 60)


async def test_code_validation():
    """测试代码验证"""
    print("\n" + "=" * 60)
    print("测试2: 代码验证")
    print("=" * 60)

    agent = StrategyAgent()

    # 生成一个策略
    result = await agent.generate_strategy(user_request="生成一个简单的均线策略")
    assert result["success"] == True

    code = result["strategy_code"]
    summary = agent._validate_code(code)

    print("\n代码验证结果:")
    print(summary)

    assert "✅" in summary, "验证结果应该包含成功标记"
    assert "策略类" in summary or "on_bar" in summary, "应该验证关键方法或类"

    print("\n✅ 测试2通过！")


async def test_class_name_extraction():
    """测试类名提取"""
    print("\n" + "=" * 60)
    print("测试3: 类名提取")
    print("=" * 60)

    agent = StrategyAgent()

    # 测试用例1：简单类名
    code1 = """
class SimpleStrategy(StrategyBase):
    def on_bar(self, context):
        return None
"""
    name1 = agent._extract_class_name(code1)
    assert name1 == "SimpleStrategy", f"应该提取到SimpleStrategy，实际: {name1}"
    print(f"✅ 测试3.1通过 - 类名: {name1}")

    # 测试用例2：带参数的类
    code2 = """
class RSI_Strategy(StrategyBase):
    def __init__(self, period=14):
        super().__init__()
        self.period = period
"""
    name2 = agent._extract_class_name(code2)
    assert name2 == "RSI_Strategy", f"应该提取到RSI_Strategy，实际: {name2}"
    print(f"✅ 测试3.2通过 - 类名: {name2}")

    # 测试用例3：没有类定义的代码
    code3 = "def on_bar(context): return None"
    name3 = agent._extract_class_name(code3)
    assert name3 == "GeneratedStrategy", f"应该返回默认名称，实际: {name3}"
    print(f"✅ 测试3.3通过 - 默认类名: {name3}")

    print("\n✅ 测试3通过！")


async def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试4: 错误处理")
    print("=" * 60)

    agent = StrategyAgent()

    # 测试无效请求（空字符串）
    print("\n测试4.1: 空请求")
    result1 = await agent.generate_strategy(user_request="")
    assert result1["success"] == False, "空请求应该失败"
    assert "error" in result1, "应该包含错误信息"
    print(f"✅ 测试4.1通过 - 错误被正确处理")

    print("\n✅ 测试4通过！")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("StrategyAgent单元测试")
    print("=" * 60)

    try:
        asyncio.run(test_strategy_generation())
        asyncio.run(test_code_validation())
        asyncio.run(test_class_name_extraction())
        asyncio.run(test_error_handling())

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
