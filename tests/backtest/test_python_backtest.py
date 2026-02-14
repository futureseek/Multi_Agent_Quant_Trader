"""
Python回测引擎集成测试

测试完整的回测流程：
1. 创建回测引擎
2. 创建策略实例
3. 注册策略
4. 加载数据
5. 运行回测
6. 获取结果
"""

import sys
import os

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.service_layer.strategy import PythonBacktestEngine, BacktestResult
from src.service_layer.strategy.examples.ma_strategy import MAStrategy


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
            'trade_date': f'202401{i:03d}',
            'symbol': '600000.SH',
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        }
        bars.append(bar)

    return bars


def test_basic_backtest():
    """基础回测测试"""
    print("=" * 60)
    print("测试1: 基础回测流程")
    print("=" * 60)

    # 1. 创建模拟数据
    bars = create_mock_data()
    print(f"✅ 创建模拟数据: {len(bars)} 根K线")

    # 2. 创建回测引擎
    engine = PythonBacktestEngine(
        initial_capital=1000000.0,
        commission_rate=0.0003,
        slippage_rate=0.0001
    )
    print("✅ 创建回测引擎")

    # 3. 创建策略实例
    strategy = MAStrategy(short_window=10, long_window=30)
    print("✅ 创建双均线策略 (10/30)")

    # 4. 注册策略
    strategy_id = engine.register_strategy(strategy)
    print(f"✅ 策略注册成功 (ID: {strategy_id})")

    # 5. 初始化回测
    engine.init(bars)
    print("✅ 回测引擎初始化")

    # 6. 运行回测
    result = engine.run()

    # 7. 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(result.summary())

    # 验证结果
    assert isinstance(result, BacktestResult), "结果应该是BacktestResult类型"
    assert len(result.equity_curve) == len(bars), "净值曲线长度应该等于K线数量"
    assert result.total_trades >= 0, "交易次数应该大于等于0"

    print("\n✅ 测试1通过！")


def test_metrics_calculation():
    """测试指标计算"""
    print("\n" + "=" * 60)
    print("测试2: 指标计算")
    print("=" * 60)

    bars = create_mock_data()
    engine = PythonBacktestEngine(initial_capital=1000000.0)
    strategy = MAStrategy(short_window=5, long_window=20)

    engine.register_strategy(strategy)
    engine.init(bars)
    result = engine.run()

    # 检查各项指标
    print(f"总收益率: {result.total_return:.4f}")
    print(f"年化收益率: {result.annual_return:.4f}")
    print(f"夏普比率: {result.sharpe_ratio:.4f}")
    print(f"最大回撤: {result.max_drawdown:.4f}")
    print(f"胜率: {result.win_rate:.4f}")
    print(f"交易次数: {result.total_trades}")
    print(f"平均每笔收益: {result.avg_profit_per_trade:.2f}")
    print(f"盈亏比: {result.profit_loss_ratio:.4f}")

    assert -1 <= result.total_return <= 10, "总收益率应该在合理范围内"
    assert -1 <= result.max_drawdown <= 0, "最大回撤应该是负数"
    assert 0 <= result.win_rate <= 1, "胜率应该在0到1之间"

    print("\n✅ 测试2通过！")


def test_context_interface():
    """测试Context接口"""
    print("\n" + "=" * 60)
    print("测试3: Context接口")
    print("=" * 60)

    from src.service_layer.strategy import SimpleContext

    bars = create_mock_data()
    engine = PythonBacktestEngine()
    engine.init(bars)

    # 创建Context
    context = SimpleContext(engine)

    # 测试get_bar（第一根bar）
    close_first = context.get_bar('600000.SH', 'close', 0)
    print(f"第一根收盘价: {close_first}")
    assert close_first == bars[0]['close'], "get_bar应该返回正确数据"

    # 手动设置current_bar_index到最后一根，获取最后一根数据
    engine.current_bar_index = len(bars) - 1
    engine.current_bar = bars[-1]
    close_last = context.get_bar('600000.SH', 'close', 0)
    print(f"最后一根收盘价: {close_last}")
    assert close_last == bars[-1]['close'], "get_bar应该返回正确数据"

    # 手动设置current_bar_index到第50根，测试get_series
    engine.current_bar_index = 50
    engine.current_bar = bars[50]
    current_close = context.get_bar('600000.SH', 'close', 0)

    # 测试get_series
    series = context.get_series('600000.SH', 'close', 10)
    print(f"最近10根收盘价: {len(series)} 个")
    assert len(series) == 10, "get_series应该返回指定数量的数据"
    assert series[-1] == current_close, "最后一个值应该是当前价格"

    # 测试get_cash
    cash = context.get_cash()
    print(f"可用资金: {cash}")
    assert cash == engine.cash, "get_cash应该返回正确金额"

    # 测试get_position
    position = context.get_position('600000.SH')
    print(f"持仓数量: {position}")
    assert position == 0, "初始持仓应该为0"

    print("\n✅ 测试3通过！")


def test_strategy_order_execution():
    """测试策略订单执行"""
    print("\n" + "=" * 60)
    print("测试4: 策略订单执行")
    print("=" * 60)

    # 创建一个简单的策略：第一根bar买入，最后一根bar卖出
    class SimpleTestStrategy:
        def __init__(self):
            self.name = "SimpleTestStrategy"
            self.context = None
            self.bar_count = 0

        def on_bar(self, context):
            self.bar_count += 1

            # 第10根bar买入
            if self.bar_count == 10:
                return {
                    'action': 'buy',
                    'symbol': '600000.SH',
                    'quantity': 100,
                    'price': context.get_bar('600000.SH', 'close', 0)
                }

            # 最后10根bar卖出
            if self.bar_count == 490:
                pos = context.get_position('600000.SH')
                if pos > 0:
                    return {
                        'action': 'sell',
                        'symbol': '600000.SH',
                        'quantity': -pos,
                        'price': context.get_bar('600000.SH', 'close', 0)
                    }

            return None

    bars = create_mock_data()
    engine = PythonBacktestEngine(initial_capital=1000000.0)
    strategy = SimpleTestStrategy()

    engine.register_strategy(strategy)
    engine.init(bars)
    result = engine.run()

    # 验证交易记录
    print(f"交易次数: {len(result.trades)}")
    print("交易明细:")
    for trade in result.trades:
        print(f"  {trade['time']} {trade['action']:4s} {trade['symbol']} {trade['quantity']:4d}股 @ {trade['price']:.2f}")

    assert len(result.trades) == 2, "应该有2笔交易（买入+卖出）"
    assert result.trades[0]['action'] == 'buy', "第一笔应该是买入"
    assert result.trades[1]['action'] == 'sell', "第二笔应该是卖出"

    # 验证持仓（通过context）
    from src.service_layer.strategy import SimpleContext
    test_context = SimpleContext(engine)
    assert test_context.get_position('600000.SH') == 0, "最终持仓应该为0"

    print("\n✅ 测试4通过！")


def test_result_serialization():
    """测试结果序列化"""
    print("\n" + "=" * 60)
    print("测试5: 结果序列化")
    print("=" * 60)

    bars = create_mock_data()
    engine = PythonBacktestEngine()
    strategy = MAStrategy(short_window=5, long_window=20)

    engine.register_strategy(strategy)
    engine.init(bars)
    result = engine.run()

    # 转换为字典
    result_dict = result.to_dict()

    # 验证字典
    required_keys = [
        'total_return', 'annual_return', 'sharpe_ratio',
        'max_drawdown', 'win_rate', 'total_trades',
        'avg_profit_per_trade', 'profit_loss_ratio',
        'equity_curve', 'trades', 'drawdowns'
    ]

    for key in required_keys:
        assert key in result_dict, f"结果字典应该包含{key}"

    print(f"结果字典包含 {len(result_dict)} 个字段")
    print(f"净值曲线长度: {len(result_dict['equity_curve'])}")
    print(f"交易记录数量: {len(result_dict['trades'])}")

    print("\n✅ 测试5通过！")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Python回测引擎集成测试")
    print("=" * 60)

    try:
        test_basic_backtest()
        test_metrics_calculation()
        test_context_interface()
        test_strategy_order_execution()
        test_result_serialization()

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
