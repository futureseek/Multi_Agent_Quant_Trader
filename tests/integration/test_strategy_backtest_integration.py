"""
策略生成与回测集成测试

测试完整的端到端流程：
1. AI生成策略代码
2. 动态加载策略类
3. 注册到回测引擎
4. 执行回测
5. 获取结果
"""

import asyncio
import sys
import os
from typing import Dict, Optional
# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.service_layer.agents.strategy_agent import StrategyAgent
from src.service_layer.agents.backtest_agent import BacktestAgent
from src.service_layer.agents.data_service_agent import DataServiceAgent
from src.service_layer.strategy.strategy_base import StrategyBase


def create_mock_data():
    """创建模拟数据用于测试"""
    import random

    bars = []
    base_price = 100.0
    for i in range(100):  # 生成100根K线
        price = base_price + random.uniform(-5, 5)
        bar = {
            'trade_date': f'202401{i+1:02d}',
            'ts_code': '600000.SH',
            'open': price,
            'high': price + random.uniform(0, 2),
            'low': price - random.uniform(0, 2),
            'close': price + random.uniform(-1, 1),
            'vol': random.randint(1000000, 10000000)
        }
        bars.append(bar)
    return bars


async def test_ma_strategy_generation_and_backtest():
    """测试1: 双均线策略生成和回测"""
    print("=" * 80)
    print("测试1: 双均线策略生成和回测")
    print("=" * 80)

    # 步骤1: 生成策略代码
    print("🤖 步骤1: 生成策略代码...")
    strategy_agent = StrategyAgent()
    
    strategy_result = await strategy_agent.generate_strategy(
        user_request="生成一个5日和20日双均线策略，金叉买入，死叉卖出",
        data_context={
            "stock_info": {"code": "600000.SH", "name": "浦发银行"},
            "date_range": ("20240101", "20240430")
        }
    )

    assert strategy_result["success"] == True, "策略生成应该成功"
    print(f"✅ 策略生成成功 - 类名: {strategy_result['strategy_name']}")
    print(f"📄 代码预览:\n{strategy_result['strategy_code']}...")

    # 步骤2: 动态加载策略类
    print("\n🔧 步骤2: 动态加载策略类...")
    
    # 修复import问题 - 在代码前添加import
    strategy_code = strategy_result['strategy_code']
    if 'from src.service_layer.strategy.strategy_base import StrategyBase' not in strategy_code:
        strategy_code = """from src.service_layer.strategy.strategy_base import StrategyBase
from typing import Dict, Optional

""" + strategy_code

    try:
        # 创建命名空间并执行代码
        namespace = {
            'StrategyBase': StrategyBase,
            'Dict': Dict,
            'Optional': Optional,
            '__builtins__': __builtins__
        }
        exec(strategy_code, namespace)
        
        # 查找策略类
        strategy_class = None
        for key, value in namespace.items():
            if isinstance(value, type) and issubclass(value, StrategyBase) and value is not StrategyBase:
                strategy_class = value
                break
        
        assert strategy_class is not None, "应该找到策略类"
        strategy_instance = strategy_class()
        print(f"✅ 策略类加载成功: {strategy_instance.name}")

    except Exception as e:
        print(f"❌ 策略类加载失败: {e}")
        print(f"🔍 代码内容:\n{strategy_code}")
        raise

    # 步骤3: 准备测试数据
    print("\n📊 步骤3: 准备测试数据...")
    bars = create_mock_data()
    print(f"✅ 模拟数据创建完成 - {len(bars)}根K线")

    # 步骤4: 执行回测
    print("\n🚀 步骤4: 执行回测...")
    backtest_agent = BacktestAgent()
    
    backtest_result = backtest_agent.run_backtest(
        strategy_code=strategy_code,
        data=bars,
        initial_capital=1000000.0
    )

    assert backtest_result["success"] == True, f"回测应该成功: {backtest_result.get('error', '')}"
    print(f"✅ 回测执行成功")

    # 步骤5: 验证结果
    print("\n📈 步骤5: 验证回测结果...")
    result = backtest_result["result"]
    
    # 验证结果结构
    required_fields = ['total_return', 'annual_return', 'sharpe_ratio', 
                      'max_drawdown', 'win_rate', 'total_trades']
    for field in required_fields:
        assert field in result, f"结果应该包含{field}"
    
    print(f"📊 回测结果摘要:")
    print(f"   总收益率: {result['total_return']:.2%}")
    print(f"   最大回撤: {result['max_drawdown']:.2%}")
    print(f"   交易次数: {result['total_trades']}")
    print(f"   胜率: {result['win_rate']:.2%}")

    print("\n✅ 测试1通过！")


async def test_rsi_strategy_generation_and_backtest():
    """测试2: RSI策略生成和回测"""
    print("\n" + "=" * 80)
    print("测试2: RSI策略生成和回测")
    print("=" * 80)

    # 生成RSI策略
    strategy_agent = StrategyAgent()
    
    strategy_result = await strategy_agent.generate_strategy(
        user_request="生成一个RSI策略，RSI小于30买入，大于70卖出，周期14天"
    )

    assert strategy_result["success"] == True, "RSI策略生成应该成功"
    print(f"✅ RSI策略生成成功 - 类名: {strategy_result['strategy_name']}")

    # 修复import并执行回测
    strategy_code = strategy_result['strategy_code']
    if 'from src.service_layer.strategy.strategy_base import StrategyBase' not in strategy_code:
        strategy_code = """from src.service_layer.strategy.strategy_base import StrategyBase
from typing import Dict, Optional

""" + strategy_code

    bars = create_mock_data()
    backtest_agent = BacktestAgent()
    
    backtest_result = backtest_agent.run_backtest(
        strategy_code=strategy_code,
        data=bars
    )

    assert backtest_result["success"] == True, f"RSI回测应该成功: {backtest_result.get('error', '')}"
    print(f"✅ RSI策略回测成功")
    
    result = backtest_result["result"]
    print(f"📊 RSI策略结果: 收益率{result['total_return']:.2%}, 交易{result['total_trades']}次")

    print("\n✅ 测试2通过！")


async def test_multiple_strategy_comparison():
    """测试3: 多策略对比"""
    print("\n" + "=" * 80)
    print("测试3: 多策略对比")
    print("=" * 80)

    strategy_agent = StrategyAgent()
    backtest_agent = BacktestAgent()
    bars = create_mock_data()

    strategies = [
        "生成一个5日均线策略",
        "生成一个10日均线策略", 
        "生成一个20日均线策略"
    ]

    results = []

    for i, strategy_desc in enumerate(strategies, 1):
        print(f"\n🔄 测试策略{i}: {strategy_desc}")
        
        # 生成策略
        strategy_result = await strategy_agent.generate_strategy(strategy_desc)
        assert strategy_result["success"] == True, f"策略{i}生成应该成功"
        
        # 修复import
        strategy_code = strategy_result['strategy_code']
        if 'from src.service_layer.strategy.strategy_base import StrategyBase' not in strategy_code:
            strategy_code = """from src.service_layer.strategy.strategy_base import StrategyBase
from typing import Dict, Optional

""" + strategy_code
        
        # 执行回测
        backtest_result = backtest_agent.run_backtest(
            strategy_code=strategy_code,
            data=bars
        )
        
        if backtest_result["success"]:
            result = backtest_result["result"]
            results.append({
                'name': strategy_result['strategy_name'],
                'description': strategy_desc,
                'total_return': result['total_return'],
                'max_drawdown': result['max_drawdown'],
                'total_trades': result['total_trades']
            })
            print(f"✅ 策略{i}完成: 收益{result['total_return']:.2%}")
        else:
            print(f"❌ 策略{i}失败: {backtest_result.get('error', 'Unknown error')}")

    # 对比结果
    print(f"\n📊 策略对比结果:")
    print(f"{'策略名':<20} {'收益率':<10} {'最大回撤':<10} {'交易次数':<10}")
    print("-" * 60)
    for result in results:
        print(f"{result['name']:<20} {result['total_return']:<10.2%} {result['max_drawdown']:<10.2%} {result['total_trades']:<10}")

    assert len(results) >= 2, "应该有至少2个成功的策略对比"
    print("\n✅ 测试3通过！")


async def test_error_handling_integration():
    """测试4: 错误处理集成测试"""
    print("\n" + "=" * 80)
    print("测试4: 错误处理集成测试")
    print("=" * 80)

    strategy_agent = StrategyAgent()
    backtest_agent = BacktestAgent()

    # 测试无效策略请求
    print("\n🧪 测试4.1: 无效策略请求")
    bad_result = await strategy_agent.generate_strategy("")
    assert bad_result["success"] == False, "空请求应该失败"
    print(f"✅ 无效请求正确处理")

    # 测试错误的策略代码
    print("\n🧪 测试4.2: 错误的策略代码")
    bad_code = """
class BadStrategy:
    def wrong_method(self):
        return "This is not a valid strategy"
"""
    
    bars = create_mock_data()
    bad_backtest = backtest_agent.run_backtest(bad_code, bars)
    assert bad_backtest["success"] == False, "错误代码应该导致回测失败"
    print(f"✅ 错误代码正确处理")

    print("\n✅ 测试4通过！")


async def run_all_integration_tests():
    """运行所有集成测试"""
    print("\n" + "=" * 80)
    print("策略生成与回测集成测试套件")
    print("=" * 80)

    try:
        await test_ma_strategy_generation_and_backtest()
        await test_rsi_strategy_generation_and_backtest()
        await test_multiple_strategy_comparison()
        await test_error_handling_integration()

        print("\n" + "=" * 80)
        print("✅ 所有集成测试通过！")
        print("🎉 AI策略生成+回测完整链路验证成功")
        print("=" * 80)

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
    asyncio.run(run_all_integration_tests())