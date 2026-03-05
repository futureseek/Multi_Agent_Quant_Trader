"""
CTA策略测试套件

验证C++引擎对各种经典CTA策略的兼容性：
1. 双均线策略（MA Cross）
2. MACD策略
3. 布林带策略（Bollinger Bands）
4. 动量策略（Momentum）
5. RSI策略
6. 通道突破策略（Channel Breakout）
"""

import sys
from pathlib import Path
import time

# 添加路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cpp_engine.python.cpp_engine import CppBacktestEngine


# ========== 数据生成工具 ==========

def generate_trending_data(n_bars=500, trend=0.0002, volatility=0.02):
    """生成带趋势的数据"""
    import random
    from datetime import datetime, timedelta

    bars = []
    base_date = datetime(2023, 1, 1)
    price = 10.0

    for i in range(n_bars):
        date_str = (base_date + timedelta(days=i)).strftime('%Y%m%d')

        # 趋势 + 随机波动
        change = random.gauss(trend, volatility)
        price = price * (1 + change)

        open_price = price
        close_price = price * (1 + random.gauss(0, 0.01))
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))

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


def generate_range_bound_data(n_bars=500):
    """生成震荡市数据"""
    import random
    from datetime import datetime, timedelta

    bars = []
    base_date = datetime(2023, 1, 1)
    base_price = 10.0

    for i in range(n_bars):
        date_str = (base_date + timedelta(days=i)).strftime('%Y%m%d')

        # 均值回归
        price = base_price + random.gauss(0, 0.3)
        price = max(price, 8.0)  # 下界
        price = min(price, 12.0)  # 上界

        open_price = price
        close_price = price + random.gauss(0, 0.05)
        high_price = max(open_price, close_price) + abs(random.gauss(0, 0.02))
        low_price = min(open_price, close_price) - abs(random.gauss(0, 0.02))

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


# ========== CTA策略实现 ==========

class MAStrategy:
    """双均线策略（金叉死叉）"""

    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window
        self.prev_ma_short = None
        self.prev_ma_long = None

    def on_bar(self, context):
        try:
            short_series = context.get_series('close', self.short_window)
            long_series = context.get_series('close', self.long_window)
        except:
            return None

        ma_short = sum(short_series) / len(short_series)
        ma_long = sum(long_series) / len(long_series)

        current_price = context.get_bar('close', 0)

        # 金叉买入
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

        # 死叉卖出
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


class MACDStrategy:
    """MACD策略（DIF金叉DEA）"""

    def __init__(self, fast=12, slow=26, signal=9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.prev_dif = None
        self.prev_dea = None

    def calculate_ema(self, data, period):
        """计算EMA"""
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append((data[i] * multiplier) + (ema[-1] * (1 - multiplier)))
        return ema

    def on_bar(self, context):
        try:
            closes = context.get_series('close', self.slow + self.signal)
        except:
            return None

        # 计算EMA
        ema_fast = self.calculate_ema(closes, self.fast)[-1]
        ema_slow = self.calculate_ema(closes, self.slow)[-1]

        dif = ema_fast - ema_slow

        # 计算DEA（DIF的EMA）
        if not hasattr(self, 'dif_history'):
            self.dif_history = []
        self.dif_history.append(dif)

        if len(self.dif_history) < self.signal:
            return None

        dea = self.calculate_ema(self.dif_history, self.signal)[-1]

        current_price = context.get_bar('close', 0)

        # DIF金叉DEA买入
        if (self.prev_dif is not None and
            self.prev_dif <= self.prev_dea and
            dif > dea):

            cash = context.get_cash()
            if cash > current_price * 100:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_price
                }

        # DIF死叉DEA卖出
        elif (self.prev_dif is not None and
              self.prev_dif >= self.prev_dea and
              dif < dea):

            position = context.get_position('TEST')
            if position > 0:
                return {
                    'action': 'sell',
                    'symbol': 'TEST',
                    'quantity': position,
                    'price': current_price
                }

        self.prev_dif = dif
        self.prev_dea = dea
        return None


class BollingerBandsStrategy:
    """布林带策略（突破上轨买入，跌破下轨卖出）"""

    def __init__(self, window=20, num_std=2):
        self.window = window
        self.num_std = num_std

    def calculate_std(self, data):
        """计算标准差"""
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5

    def on_bar(self, context):
        try:
            closes = context.get_series('close', self.window)
        except:
            return None

        middle = sum(closes) / len(closes)
        std = self.calculate_std(closes)

        upper = middle + self.num_std * std
        lower = middle - self.num_std * std

        current_price = context.get_bar('close', 0)

        position = context.get_position('TEST')

        # 突破上轨买入
        if current_price > upper and position == 0:
            cash = context.get_cash()
            if cash > current_price * 100:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_price
                }

        # 跌破下轨卖出
        elif current_price < lower and position > 0:
            return {
                'action': 'sell',
                'symbol': 'TEST',
                'quantity': position,
                'price': current_price
            }

        # 回归中轨平仓
        elif position > 0 and abs(current_price - middle) < std * 0.5:
            return {
                'action': 'sell',
                'symbol': 'TEST',
                'quantity': position,
                'price': current_price
            }

        return None


class MomentumStrategy:
    """动量策略（价格创N日新高买入）"""

    def __init__(self, lookback=20):
        self.lookback = lookback

    def on_bar(self, context):
        try:
            highs = context.get_series('high', self.lookback)
            closes = context.get_series('close', self.lookback)
        except:
            return None

        current_high = context.get_bar('high', 0)
        current_close = context.get_bar('close', 0)

        position = context.get_position('TEST')

        # 创新高买入
        if current_high > max(highs[:-1]) and position == 0:
            cash = context.get_cash()
            if cash > current_close * 100:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_close
                }

        # 跌破最近低点止损
        elif position > 0:
            recent_low = min(closes[:-5]) if len(closes) > 5 else min(closes[:-1])
            if current_close < recent_low:
                return {
                    'action': 'sell',
                    'symbol': 'TEST',
                    'quantity': position,
                    'price': current_close
                }

        return None


class RSIStrategy:
    """RSI策略（超买超卖）"""

    def __init__(self, period=14, oversold=30, overbought=70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def calculate_rsi(self, closes):
        """计算RSI"""
        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-change)

        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def on_bar(self, context):
        try:
            closes = context.get_series('close', self.period + 5)
        except:
            return None

        rsi = self.calculate_rsi(closes)
        current_price = context.get_bar('close', 0)

        position = context.get_position('TEST')

        # 超卖买入
        if rsi < self.oversold and position == 0:
            cash = context.get_cash()
            if cash > current_price * 100:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_price
                }

        # 超买卖出
        elif rsi > self.overbought and position > 0:
            return {
                'action': 'sell',
                'symbol': 'TEST',
                'quantity': position,
                'price': current_price
            }

        return None


class ChannelBreakoutStrategy:
    """通道突破策略（唐奇安通道）"""

    def __init__(self, lookback=20):
        self.lookback = lookback

    def on_bar(self, context):
        try:
            highs = context.get_series('high', self.lookback)
            lows = context.get_series('low', self.lookback)
        except:
            return None

        upper_channel = max(highs[:-1])
        lower_channel = min(lows[:-1])

        current_high = context.get_bar('high', 0)
        current_low = context.get_bar('low', 0)
        current_close = context.get_bar('close', 0)

        position = context.get_position('TEST')

        # 向上突破
        if current_high > upper_channel and position == 0:
            cash = context.get_cash()
            if cash > current_close * 100:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_close
                }

        # 向下突破
        elif current_low < lower_channel and position > 0:
            return {
                'action': 'sell',
                'symbol': 'TEST',
                'quantity': position,
                'price': current_close
            }

        return None


# ========== 测试框架 ==========

def test_strategy(name, strategy, data, description):
    """测试单个策略"""
    print(f"\n{'=' * 70}")
    print(f"策略: {name}")
    print(f"描述: {description}")
    print(f"{'=' * 70}")

    engine = CppBacktestEngine(initial_capital=1000000.0, commission_rate=0.0003)
    engine.init(data)
    engine.register_strategy(strategy)

    start_time = time.time()
    result = engine.run_backtest()
    elapsed = time.time() - start_time

    print(f"\n⏱️  执行时间: {elapsed:.4f}秒")
    print(f"📊 速度: {len(data)/elapsed:.0f} bars/sec")

    return {
        'name': name,
        'description': description,
        'result': result,
        'elapsed': elapsed
    }


def main():
    """主测试函数"""
    print("\n" + "🚀" * 35)
    print("C++引擎CTA策略兼容性测试")
    print("🚀" * 35)

    # 生成测试数据
    print("\n📊 生成测试数据...")
    trending_data = generate_trending_data(1000, trend=0.0003, volatility=0.015)
    range_data = generate_range_bound_data(1000)
    print(f"   趋势市数据: {len(trending_data)} 根K线")
    print(f"   震荡市数据: {len(range_data)} 根K线")

    # 定义测试用例
    test_cases = [
        # 趋势市策略
        {
            'name': '双均线策略 (MA Cross)',
            'strategy': MAStrategy(short_window=5, long_window=20),
            'data': trending_data,
            'description': '金叉买入，死叉卖出 - 适合趋势市场'
        },
        {
            'name': 'MACD策略',
            'strategy': MACDStrategy(fast=12, slow=26, signal=9),
            'data': trending_data,
            'description': 'DIF金叉DEA买入 - 趋势跟踪指标'
        },
        {
            'name': '动量策略 (Momentum)',
            'strategy': MomentumStrategy(lookback=20),
            'data': trending_data,
            'description': '创20日新高买入 - 趋势延续'
        },
        {
            'name': '通道突破策略 (Channel Breakout)',
            'strategy': ChannelBreakoutStrategy(lookback=20),
            'data': trending_data,
            'description': '突破唐奇安通道 - 趋势启动'
        },

        # 震荡市策略
        {
            'name': '布林带策略 (Bollinger Bands)',
            'strategy': BollingerBandsStrategy(window=20, num_std=2),
            'data': range_data,
            'description': '突破上轨买入，回归中轨卖出 - 适合震荡市'
        },
        {
            'name': 'RSI策略',
            'strategy': RSIStrategy(period=14, oversold=30, overbought=70),
            'data': range_data,
            'description': '超卖区买入，超买区卖出 - 均值回归'
        },
    ]

    # 运行测试
    results = []
    for test_case in test_cases:
        try:
            result = test_strategy(
                test_case['name'],
                test_case['strategy'],
                test_case['data'],
                test_case['description']
            )
            results.append(result)
        except Exception as e:
            print(f"\n❌ 策略 {test_case['name']} 测试失败: {e}")
            import traceback
            traceback.print_exc()

    # 生成总结报告
    print("\n" + "=" * 70)
    print("测试总结报告")
    print("=" * 70)

    print(f"\n{'策略名称':<30} {'收益率':<12} {'夏普比率':<10} {'交易次数':<8} {'耗时(秒)':<10}")
    print("-" * 70)

    total_trades = 0
    total_elapsed = 0

    for r in results:
        res = r['result']
        print(f"{r['name']:<30} {res.total_return:>10.2%}  {res.sharpe_ratio:>8.2f}   "
              f"{res.total_trades:>6}   {r['elapsed']:>8.4f}")
        total_trades += res.total_trades
        total_elapsed += r['elapsed']

    print("-" * 70)
    print(f"{'总计':<30} {'':<12} {'':<10} {total_trades:>6}   {total_elapsed:>8.4f}")

    # 统计成功率
    success_count = sum(1 for r in results if r['result'].total_trades > 0)
    print(f"\n✅ 成功运行策略: {success_count}/{len(results)}")

    if success_count == len(results):
        print("\n🎉 所有CTA策略测试通过！C++引擎接口兼容性验证成功！")
    else:
        print(f"\n⚠️  有 {len(results) - success_count} 个策略未能产生交易")

    return 0


if __name__ == "__main__":
    exit(main())
