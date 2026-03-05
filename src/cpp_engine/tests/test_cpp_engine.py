"""
C++回测引擎测试脚本

测试双均线策略，验证：
1. C++引擎能正确执行策略
2. 接口兼容性
3. 性能对比
"""

import sys
import time
from pathlib import Path

# 添加路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cpp_engine.python.cpp_engine import CppBacktestEngine


class TestMAStrategy:
    """测试用双均线策略"""

    def __init__(self, short_window: int = 5, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window
        self.prev_ma_short = None
        self.prev_ma_long = None

    def on_bar(self, context):
        """每根K线回调"""
        try:
            # 尝试获取数据
            short_series = context.get_series('close', self.short_window)
            long_series = context.get_series('close', self.long_window)
        except Exception:
            # 数据不足，跳过
            return None

        # 计算均线
        ma_short = sum(short_series) / len(short_series)
        ma_long = sum(long_series) / len(long_series)

        # 获取当前价格和日期
        try:
            close_price = context.get_bar('close', 0)
            current_date = context.get_current_date()
        except Exception:
            return None

        # 判断交易信号
        if (self.prev_ma_short is not None and
            self.prev_ma_long is not None):

            # 金叉：买入
            if (self.prev_ma_short <= self.prev_ma_long and
                ma_short > ma_long):

                cash = context.get_cash()
                if cash > close_price * 100:
                    return {
                        'action': 'buy',
                        'symbol': 'TEST',
                        'quantity': 100,
                        'price': close_price
                    }

            # 死叉：卖出
            elif (self.prev_ma_short >= self.prev_ma_long and
                  ma_short < ma_long):

                position = context.get_position('TEST')
                if position > 0:
                    return {
                        'action': 'sell',
                        'symbol': 'TEST',
                        'quantity': position,
                        'price': close_price
                    }

        # 更新均线
        self.prev_ma_short = ma_short
        self.prev_ma_long = ma_long

        return None


def generate_test_data(n_bars=500):
    """生成模拟测试数据"""
    import random
    from datetime import datetime, timedelta

    bars = []
    base_date = datetime(2023, 1, 1)

    # 模拟价格走势（包含趋势和波动）
    price = 10.0
    trend = 0.0001  # 轻微上涨趋势

    for i in range(n_bars):
        date_str = (base_date + timedelta(days=i)).strftime('%Y%m%d')

        # 随机游走
        change = random.gauss(trend, 0.02)
        price = price * (1 + change)

        # 生成OHLC
        open_price = price
        close_price = price * (1 + random.gauss(0, 0.01))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))

        # 生成成交量和成交额
        vol = int(random.gauss(1000000, 200000))
        vol = max(vol, 100000)
        amount = vol * close_price

        bars.append({
            'trade_date': date_str,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'vol': vol,
            'amount': round(amount, 2)
        })

    return bars


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试1: 基本功能测试")
    print("=" * 60)

    # 生成测试数据
    print("\n📊 生成测试数据...")
    bars = generate_test_data(500)
    print(f"   生成了 {len(bars)} 根K线")

    # 创建引擎
    print("\n⚙️  创建C++引擎...")
    engine = CppBacktestEngine(initial_capital=1000000.0, commission_rate=0.0003)

    # 初始化
    print("\n🔧 初始化引擎...")
    engine.init(bars)

    # 创建策略
    print("\n📈 创建双均线策略...")
    strategy = TestMAStrategy(short_window=5, long_window=20)

    # 注册策略
    print("\n✅ 注册策略...")
    engine.register_strategy(strategy)

    # 运行回测
    print("\n🚀 运行回测...")
    result = engine.run_backtest()

    # 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"总收益率: {result.total_return:.2%}")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"最大回撤: {result.max_drawdown:.2%}")
    print(f"交易次数: {result.total_trades}")
    print(f"胜率: {result.win_rate:.2%}")
    print(f"最终资产: {1000000 * (1 + result.total_return):,.2f}")

    return result


def test_interface_compatibility():
    """测试接口兼容性"""
    print("\n" + "=" * 60)
    print("测试2: 接口兼容性测试")
    print("=" * 60)

    bars = generate_test_data(100)
    engine = CppBacktestEngine()
    engine.init(bars)

    class TestStrategy:
        def __init__(self):
            self.test_results = []

        def on_bar(self, context):
            # 测试各种接口
            try:
                # get_series
                series = context.get_series('close', 10)
                assert len(series) == 10, "get_series返回长度错误"
                assert isinstance(series[0], float), "get_series返回类型错误"

                # get_bar
                close = context.get_bar('close', 0)
                assert isinstance(close, float), "get_bar返回类型错误"

                # get_current_date
                date = context.get_current_date()
                assert isinstance(date, str), "get_current_date返回类型错误"

                # get_cash
                cash = context.get_cash()
                assert isinstance(cash, float), "get_cash返回类型错误"
                assert cash > 0, "现金应该大于0"

                # get_position
                pos = context.get_position('TEST')
                assert isinstance(pos, int), "get_position返回类型错误"

                self.test_results.append(True)
            except Exception as e:
                print(f"   ❌ 接口测试失败: {e}")
                self.test_results.append(False)

            return None

    strategy = TestStrategy()
    engine.register_strategy(strategy)
    engine.run_backtest()

    success_rate = sum(strategy.test_results) / len(strategy.test_results)
    print(f"\n✅ 接口兼容性测试通过率: {success_rate:.1%}")

    return success_rate == 1.0


def test_performance():
    """测试性能"""
    print("\n" + "=" * 60)
    print("测试3: 性能测试")
    print("=" * 60)

    # 测试不同数据量的性能
    sizes = [1000, 5000, 10000]

    for size in sizes:
        print(f"\n📊 测试 {size} 根K线...")

        bars = generate_test_data(size)
        engine = CppBacktestEngine()
        engine.init(bars)
        strategy = TestMAStrategy()
        engine.register_strategy(strategy)

        # 计时
        start_time = time.time()
        result = engine.run_backtest()
        elapsed = time.time() - start_time

        print(f"   ⏱️  耗时: {elapsed:.4f}秒")
        print(f"   📈 速度: {size/elapsed:.0f} bars/sec")

    return True


def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("C++回测引擎测试")
    print("🚀" * 30)

    try:
        # 测试1: 基本功能
        result1 = test_basic_functionality()

        # 测试2: 接口兼容性
        result2 = test_interface_compatibility()

        # 测试3: 性能
        result3 = test_performance()

        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"✅ 基本功能测试: {'通过' if result1 else '失败'}")
        print(f"✅ 接口兼容性测试: {'通过' if result2 else '失败'}")
        print(f"✅ 性能测试: {'完成' if result3 else '失败'}")

        if result1 and result2 and result3:
            print("\n🎉 所有测试通过！C++引擎可以正常工作。")
        else:
            print("\n⚠️  部分测试失败，请检查。")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
