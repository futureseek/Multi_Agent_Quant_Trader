"""
示例策略：双均线策略

这是最经典的技术分析策略之一：
- 短期均线上穿长期均线（金叉）时买入
- 短期均线下穿长期均线（死叉）时卖出
"""

from typing import Dict, Optional
import sys
import os

# 添加上级目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.service_layer.strategy.strategy_base import StrategyBase


class MAStrategy(StrategyBase):
    """
    双均线策略

    策略逻辑：
    1. 计算短期均线和长期均线
    2. 当短期均线上穿长期均线（金叉）时买入
    3. 当短期均线下穿长期均线（死叉）时卖出
    """

    def __init__(self, short_window: int = 5, long_window: int = 20):
        """
        初始化双均线策略

        Args:
            short_window: 短期均线窗口
            long_window: 长期均线窗口
        """
        super().__init__()

        if short_window >= long_window:
            raise ValueError("短期均线窗口必须小于长期均线窗口")

        self.short_window = short_window
        self.long_window = long_window

        # 记录上一根K线的均线值，用于判断金叉死叉
        self.prev_ma_short = None
        self.prev_ma_long = None

        print(f"✅ {self.name} 初始化")
        print(f"   短期均线窗口: {short_window}")
        print(f"   长期均线窗口: {long_window}")

    def on_bar(self, context) -> Optional[Dict]:
        """
        每根K线回调

        Args:
            context: 上下文对象

        Returns:
            订单字典或None
        """
        # 获取当前日期
        current_date = context.get_current_date()

        # 获取当前价格
        try:
            close_price = context.get_bar('600000.SH', 'close', 0)
        except (KeyError, IndexError):
            # 当前bar没有数据，跳过
            return None

        # 数据不足时跳过
        try:
            short_series = context.get_series('600000.SH', 'close', self.short_window)
            long_series = context.get_series('600000.SH', 'close', self.long_window)
        except IndexError:
            # 数据不足，无法计算均线
            return None

        # 计算均线
        ma_short = sum(short_series) / len(short_series)
        ma_long = sum(long_series) / len(long_series)

        # 判断交易信号
        order = None

        # 买入信号：金叉（短期均线上穿长期均线）
        if (self.prev_ma_short is not None and
            self.prev_ma_long is not None and
            self.prev_ma_short <= self.prev_ma_long and
            ma_short > ma_long):

            cash = context.get_cash()
            if cash > 0:
                # 计算买入数量（固定100股或全仓）
                quantity = 100  # 简化处理，固定买入100股

                order = {
                    'action': 'buy',
                    'symbol': '600000.SH',
                    'quantity': quantity,
                    'price': close_price
                }

                print(f"   📈 金叉信号 ({current_date}): MA{self.short_window}={ma_short:.2f} > MA{self.long_window}={ma_long:.2f}")

        # 卖出信号：死叉（短期均线下穿长期均线）
        elif (self.prev_ma_short is not None and
              self.prev_ma_long is not None and
              self.prev_ma_short >= self.prev_ma_long and
              ma_short < ma_long):

            position = context.get_position('600000.SH')
            if position > 0:
                order = {
                    'action': 'sell',
                    'symbol': '600000.SH',
                    'quantity': -position,  # 清空持仓
                    'price': close_price
                }

                print(f"   📉 死叉信号 ({current_date}): MA{self.short_window}={ma_short:.2f} < MA{self.long_window}={ma_long:.2f}")

        # 更新上一根K线的均线值
        self.prev_ma_short = ma_short
        self.prev_ma_long = ma_long

        return order

    def on_end(self, context) -> None:
        """回测结束回调"""
        print(f"\n=== {self.name} 回测结束 ===")
        print(f"最终持仓: {context.get_position('600000.SH')} 股")
        print(f"剩余现金: {context.get_cash():,.2f}")
        print(f"总资产: {context.get_total_asset():,.2f}")
