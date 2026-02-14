"""
SimpleContext - 简单的上下文对象

为Python策略提供数据访问和交易接口
这是Python版本的上下文对象，后续会被C++的StrategyContext替换
"""

from typing import Dict, List, Optional
from datetime import datetime


class SimpleContext:
    """
    简单的上下文对象

    提供给Python策略的数据访问和交易接口
    设计与设计文档中的StrategyContext接口保持一致
    """

    def __init__(self, engine: 'PythonBacktestEngine'):
        """
        初始化上下文

        Args:
            engine: 回测引擎实例
        """
        self._engine = engine

    def get_bar(self, symbol: str, field: str, offset: int = 0) -> float:
        """
        获取单根K线的某个字段

        Args:
            symbol: 股票代码，如 '600000.SH'
            field: 字段名，如 'open', 'high', 'low', 'close', 'volume'
            offset: 偏移量，0表示当前bar，1表示前1根bar

        Returns:
            字段值

        Raises:
            IndexError: 当偏移量超出范围时
            KeyError: 当字段不存在时
        """
        bars = self._engine.bars
        current_index = self._engine.current_bar_index

        if offset > current_index:
            raise IndexError(f"Offset {offset} exceeds available bars")

        target_index = current_index - offset
        bar = bars[target_index]

        if field not in bar:
            raise KeyError(f"Field '{field}' not found in bar")

        return bar[field]

    def get_series(self, symbol: str, field: str, count: int) -> List[float]:
        """
        获取序列数据

        Args:
            symbol: 股票代码
            field: 字段名
            count: 获取数量

        Returns:
            字段值列表，按时间顺序排列（从旧到新）

        Raises:
            IndexError: 当请求数量超出范围时
            KeyError: 当字段不存在时
        """
        bars = self._engine.bars
        current_index = self._engine.current_bar_index

        if count > current_index + 1:
            raise IndexError(f"Requested {count} bars, but only {current_index + 1} available")

        start_index = current_index - count + 1
        series = [bars[i][field] for i in range(start_index, current_index + 1)]

        return series

    def buy(self, symbol: str, quantity: int, price: float) -> None:
        """
        下买单

        Args:
            symbol: 股票代码
            quantity: 买入数量
            price: 买入价格
        """
        order = {
            'order_id': self._engine._generate_order_id(),
            'symbol': symbol,
            'action': 'buy',
            'quantity': quantity,
            'price': price,
            'status': 'pending',
            'time': self._engine.current_bar.get('trade_date', '')
        }

        self._engine._add_order(order)

    def sell(self, symbol: str, quantity: int, price: float) -> None:
        """
        下卖单

        Args:
            symbol: 股票代码
            quantity: 卖出数量
            price: 卖出价格
        """
        order = {
            'order_id': self._engine._generate_order_id(),
            'symbol': symbol,
            'action': 'sell',
            'quantity': quantity,
            'price': price,
            'status': 'pending',
            'time': self._engine.current_bar.get('trade_date', '')
        }

        self._engine._add_order(order)

    def cancel_order(self, order_id: str) -> None:
        """
        撤销订单

        Args:
            order_id: 订单ID
        """
        self._engine._cancel_order(order_id)

    def get_cash(self) -> float:
        """
        获取可用资金

        Returns:
            可用资金
        """
        return self._engine.cash

    def get_position(self, symbol: str) -> int:
        """
        获取持仓数量

        Args:
            symbol: 股票代码

        Returns:
            持仓数量（正数表示多头，负数表示空头）
        """
        return self._engine.positions.get(symbol, 0)

    def get_total_asset(self) -> float:
        """
        获取总资产（现金+持仓市值）

        Returns:
            总资产
        """
        return self._engine._get_total_asset()

    def get_current_bar(self) -> Dict:
        """
        获取当前K线数据

        Returns:
            当前K线数据字典
        """
        return self._engine.current_bar

    def get_current_date(self) -> str:
        """
        获取当前日期

        Returns:
            当前日期（YYYYMMDD格式）
        """
        return self._engine.current_bar.get('trade_date', '')

    def get_bars_up_to_now(self) -> List[Dict]:
        """
        获取截至当前的所有K线数据

        Returns:
            K线数据列表
        """
        return self._engine.bars[:self._engine.current_bar_index + 1]
