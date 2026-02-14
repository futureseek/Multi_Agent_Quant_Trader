"""
BacktestAgent单元测试
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.service_layer.agents.backtest_agent import BacktestAgent


def create_mock_data():
    """
    创建模拟K线数据

    生成一个简单的上升趋势数据，便于测试
    """
    import random

    bars = []
    base_price = 100.0
    trend = 0.001  # 每日上涨0.1%

    for i in range(500):  # 生成500根K线
        # 添加趋势和随机波动
        price = base_price * (1 + trend * i) * (1 + random.uniform(-0.02, 0.02))

        # 生成K线数据
        high = price * (1 + random.uniform(0, 0.02))
        low = price * (1 - random.uniform(0, 0.02))
        open_price = random.uniform(low, high)
        close = random.uniform(low, high)
        volume = random.randint(1000000, 10000000)

        bar = {
            'trade_date': f'2024{i:03d}',
            'symbol': '600000.SH',
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        }
        bars.append(bar)

    return bars


def get_sample_strategy_code():
    """返回示例策略代码"""
    return """
from src.service_layer.strategy.strategy_base import StrategyBase

class MAStrategy(StrategyBase):
    def __init__(self, short=5, long=20):
        super().__init__()
        self.short = short
        self.long = long
        self.prev_ma_short = None
        self.prev_ma_long = None

    def on_bar(self, context):
        try:
            short_series = context.get_series('600000.SH', 'close', self.short)
            long_series = context.get_series('600000.SH', 'close', self.long)

            ma_short = sum(short_series) / len(short_series)
            ma_long = sum(long_series) / len(long_series)

            if (self.prev_ma_short is not None and
                self.prev_ma_long is not None and
                self.prev_ma_short <= self.prev_ma_long and
                ma_short > ma_long):

                if context.get_cash() > 0:
                    return {
                        'action': 'buy',
                        'symbol': '600000.SH',
                        'quantity': 100,
                        'price': context.get_bar('600000.SH', 'close', 0)
                    }

            elif (self.prev_ma_short is not None and
                  self.prev_ma_long is not None and
                  self.prev_ma_short >= self.prev_ma_long and
                  ma_short < ma_long):

                position = context.get_position('600000.SH')
                if position > 0:
                    return {
                        'action': 'sell',
                        'symbol': '600000.SH',
                        'quantity': -position,
                        'price': context.get_bar('600000.SH', 'close', 0)
                    }

            self.prev_ma_short = ma_short
            self.prev_ma_long = ma_long

        except (KeyError, IndexError):
            pass

        return None
"""


def test_backtest_execution():
    """测试回测执行"""
    print("=" * 60)
    print("测试1: 回测执行")
    print("=" * 60)

    agent = BacktestAgent()
    data = create_mock_data()
    strategy_code = get_sample_strategy_code()

    # 执行回测
    result = agent.run_backtest(
        strategy_code=strategy_code,
        data=data
    )

    # 验证结果
    assert result["success"] == True, "回测应该成功"
    assert "result" in result, "结果应该包含result"
    assert "summary" in result, "结果应该包含summary"

    print(f"\n✅ 测试1通过 - 回测执行成功")

    # 打印回测摘要
    print(result["summary"])


def test_backtest_result_validation():
    """测试回测结果验证"""
    print("\n" + "=" * 60)
    print("测试2: 回测结果验证")
    print("=" * 60)

    agent = BacktestAgent()
    data = create_mock_data()
    strategy_code = get_sample_strategy_code()

    result = agent.run_backtest(
        strategy_code=strategy_code,
        data=data
    )

    backtest_result = result["result"]

    # 验证关键指标
    assert "total_return" in backtest_result, "结果应该包含total_return"
    assert "annual_return" in backtest_result, "结果应该包含annual_return"
    assert "sharpe_ratio" in backtest_result, "结果应该包含sharpe_ratio"
    assert "max_drawdown" in backtest_result, "结果应该包含max_drawdown"
    assert "win_rate" in backtest_result, "结果应该包含win_rate"
    assert "total_trades" in backtest_result, "结果应该包含total_trades"
    assert "equity_curve" in backtest_result, "结果应该包含equity_curve"

    # 验证指标值范围
    assert backtest_result["total_trades"] >= 0, "交易次数应该>=0"
    assert backtest_result["win_rate"] >= 0 and backtest_result["win_rate"] <= 1, "胜率应该在0-1之间"
    assert backtest_result["max_drawdown"] <= 0, "最大回撤应该是负数或0"

    print(f"\n总收益率: {backtest_result['total_return']:.4f}")
    print(f"年化收益率: {backtest_result['annual_return']:.4f}")
    print(f"夏普比率: {backtest_result['sharpe_ratio']:.4f}")
    print(f"最大回撤: {backtest_result['max_drawdown']:.4f}")
    print(f"胜率: {backtest_result['win_rate']:.4f}")
    print(f"交易次数: {backtest_result['total_trades']}")
    print(f"净值曲线长度: {len(backtest_result['equity_curve'])}")

    print("\n✅ 测试2通过 - 回测结果验证成功")


def test_strategy_code_loading():
    """测试策略代码加载"""
    print("\n" + "=" * 60)
    print("测试3: 策略代码加载")
    print("=" * 60)

    agent = BacktestAgent()

    # 测试1：加载有效策略
    print("\n测试3.1: 加载有效策略代码")
    valid_code = get_sample_strategy_code()
    strategy = agent._load_strategy_from_code(valid_code)
    assert strategy is not None, "应该成功加载策略"
    assert hasattr(strategy, 'on_bar'), "策略应该有on_bar方法"
    print(f"✅ 测试3.1通过 - 成功加载策略类: {strategy.__class__.__name__}")

    # 测试2：加载无效策略（缺少class）
    print("\n测试3.2: 加载无效策略代码")
    invalid_code = "def on_bar(context): return None"
    strategy = agent._load_strategy_from_code(invalid_code)
    assert strategy is None, "应该返回None"
    print(f"✅ 测试3.2通过 - 正确识别无效代码")

    # 测试3：加载缺少on_bar方法的类
    print("\n测试3.3: 加载缺少on_bar方法的类")
    incomplete_code = """
from src.service_layer.strategy.strategy_base import StrategyBase

class IncompleteStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
"""
    strategy = agent._load_strategy_from_code(incomplete_code)
    assert strategy is None, "应该返回None"
    print(f"✅ 测试3.3通过 - 正确识别缺少on_bar方法的类")

    print("\n✅ 测试3通过！")


def test_different_parameters():
    """测试不同回测参数"""
    print("\n" + "=" * 60)
    print("测试4: 不同回测参数")
    print("=" * 60)

    agent = BacktestAgent()
    data = create_mock_data()
    strategy_code = get_sample_strategy_code()

    # 测试1：不同的初始资金
    print("\n测试4.1: 不同的初始资金")
    result1 = agent.run_backtest(
        strategy_code=strategy_code,
        data=data,
        initial_capital=500000.0
    )
    assert result1["success"] == True, "回测应该成功"
    print(f"✅ 测试4.1通过 - 初始资金50万回测成功")

    # 测试2：不同的手续费率
    print("\n测试4.2: 不同的手续费率")
    result2 = agent.run_backtest(
        strategy_code=strategy_code,
        data=data,
        commission_rate=0.0001
    )
    assert result2["success"] == True, "回测应该成功"
    print(f"✅ 测试4.2通过 - 手续费率0.01%回测成功")

    # 测试3：不同的滑点率
    print("\n测试4.3: 不同的滑点率")
    result3 = agent.run_backtest(
        strategy_code=strategy_code,
        data=data,
        slippage_rate=0.0002
    )
    assert result3["success"] == True, "回测应该成功"
    print(f"✅ 测试4.3通过 - 滑点率0.02%回测成功")

    print("\n✅ 测试4通过！")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 60)
    print("测试5: 错误处理")
    print("=" * 60)

    agent = BacktestAgent()

    # 测试1：无效的策略代码
    print("\n测试5.1: 无效的策略代码")
    result1 = agent.run_backtest(
        strategy_code="invalid code",
        data=create_mock_data()
    )
    assert result1["success"] == False, "回测应该失败"
    assert "error" in result1, "应该包含错误信息"
    print(f"✅ 测试5.1通过 - 无效代码被正确处理")

    # 测试2：空数据
    print("\n测试5.2: 空数据")
    result2 = agent.run_backtest(
        strategy_code=get_sample_strategy_code(),
        data=[]
    )
    assert result2["success"] == False, "回测应该失败"
    assert "error" in result2, "应该包含错误信息"
    print(f"✅ 测试5.2通过 - 空数据被正确处理")

    print("\n✅ 测试5通过！")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("BacktestAgent单元测试")
    print("=" * 60)

    try:
        test_backtest_execution()
        test_backtest_result_validation()
        test_strategy_code_loading()
        test_different_parameters()
        test_error_handling()

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
