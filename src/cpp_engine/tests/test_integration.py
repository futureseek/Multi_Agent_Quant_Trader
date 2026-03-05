"""
集成测试：验证C++引擎与BacktestAgent的集成

测试整个回测流程：
1. BacktestAgent加载策略代码
2. 使用C++引擎执行回测
3. 返回结果
"""

import sys
from pathlib import Path

# 添加路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.service_layer.agents.backtest_agent import BacktestAgent


# 生成测试数据
def generate_test_data(n_bars=200):
    """生成简单测试数据"""
    import random
    from datetime import datetime, timedelta

    bars = []
    base_date = datetime(2023, 1, 1)
    price = 10.0

    for i in range(n_bars):
        date_str = (base_date + timedelta(days=i)).strftime('%Y%m%d')
        change = random.gauss(0.0001, 0.015)
        price = price * (1 + change)

        bars.append({
            'trade_date': date_str,
            'open': round(price, 2),
            'high': round(price * 1.01, 2),
            'low': round(price * 0.99, 2),
            'close': round(price, 2),
            'vol': 1000000,
            'amount': round(price * 1000000, 2)
        })

    return bars


# 测试策略代码
TEST_STRATEGY_CODE = """
class TestMAStrategy(StrategyBase):
    def __init__(self):
        self.prev_ma_short = None
        self.prev_ma_long = None

    def on_bar(self, context):
        try:
            short_series = context.get_series('close', 5)
            long_series = context.get_series('close', 20)
        except:
            return None

        ma_short = sum(short_series) / len(short_series)
        ma_long = sum(long_series) / len(long_series)
        current_price = context.get_bar('close', 0)

        if (self.prev_ma_short is not None and
            self.prev_ma_short <= self.prev_ma_long and
            ma_short > ma_long):

            cash = context.get_cash()
            if cash > current_price * 100:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_price
                }

        elif (self.prev_ma_short is not None and
              self.prev_ma_short >= self.prev_ma_long and
              ma_short < ma_long):

            position = context.get_position('TEST')
            if position > 0:
                return {
                    'action': 'sell',
                    'symbol': 'TEST',
                    'quantity': position,
                    'price': current_price
                }

        self.prev_ma_short = ma_short
        self.prev_ma_long = ma_long
        return None
"""


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("C++引擎集成测试")
    print("=" * 70)

    # 1. 创建BacktestAgent
    print("\n✅ 创建BacktestAgent...")
    agent = BacktestAgent()

    # 2. 生成测试数据
    print("\n✅ 生成测试数据...")
    data = generate_test_data(200)
    print(f"   数据量: {len(data)} 根K线")

    # 3. 运行回测
    print("\n✅ 开始回测...")
    result = agent.run_backtest(
        strategy_code=TEST_STRATEGY_CODE,
        data=data,
        initial_capital=1000000.0,
        commission_rate=0.0003
    )

    # 4. 检查结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)

    if result.get('success'):
        print("✅ 回测成功！")
        print("\n" + result.get('summary', ''))

        metrics = result.get('result', {})
        print(f"\n详细指标:")
        print(f"  总收益率: {metrics.get('total_return', 0):.2%}")
        print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  最大回撤: {metrics.get('max_drawdown', 0):.2%}")
        print(f"  交易次数: {metrics.get('total_trades', 0)}")
        print(f"  胜率: {metrics.get('win_rate', 0):.2%}")

        # 验证基本合理性
        assert 'total_return' in metrics, "缺少total_return"
        assert 'sharpe_ratio' in metrics, "缺少sharpe_ratio"
        assert 'max_drawdown' in metrics, "缺少max_drawdown"
        assert 'total_trades' in metrics, "缺少total_trades"

        print("\n🎉 所有测试通过！C++引擎集成成功！")
        return 0
    else:
        print(f"❌ 回测失败: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    exit(main())
