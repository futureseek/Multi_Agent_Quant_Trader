"""
Python回测引擎 - MVP版本

纯Python实现的回测引擎，用于验证设计思路
后续会被C++引擎替换，但接口保持一致
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from .strategy_base import StrategyBase, BacktestResult
from .simple_context import SimpleContext


class PythonBacktestEngine:
    """
    Python回测引擎

    功能：
    - 加载历史数据
    - 运行策略回测
    - 计算绩效指标
    """

    def __init__(self,
                 initial_capital: float = 1000000.0,
                 commission_rate: float = 0.0003,
                 slippage_rate: float = 0.0001):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率（默认0.03%）
            slippage_rate: 滑点率（默认0.01%）
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        # 回测状态
        self.cash = initial_capital
        self.positions: Dict[str, int] = {}  # symbol -> quantity
        self.bars: List[Dict] = []  # K线数据
        self.current_bar_index = 0
        self.current_bar: Dict = {}

        # 订单和交易
        self.pending_orders: List[Dict] = []
        self.orders: List[Dict] = []  # 所有订单
        self.trades: List[Dict] = []  # 所有成交

        # 净值曲线
        self.equity_curve: List[float] = []

        # 订单计数器
        self._order_counter = 0

        # 策略实例
        self.strategy: Optional[StrategyBase] = None
        self.context: Optional[SimpleContext] = None

    def init(self, bars: List[Dict]) -> None:
        """
        初始化回测

        Args:
            bars: K线数据列表
        """
        self.bars = bars
        self._reset()

        print(f"✅ 回测引擎初始化完成")
        print(f"   - 初始资金: {self.initial_capital:,.2f}")
        print(f"   - K线数量: {len(bars)}")
        print(f"   - 时间范围: {bars[0]['trade_date']} ~ {bars[-1]['trade_date']}")

    def _reset(self) -> None:
        """重置回测状态"""
        self.cash = self.initial_capital
        self.positions = {}
        self.current_bar_index = 0
        self.current_bar = {}
        self.pending_orders = []
        self.orders = []
        self.trades = []
        self.equity_curve = []
        self._order_counter = 0

    def register_strategy(self, strategy: StrategyBase) -> int:
        """
        注册策略

        Args:
            strategy: 策略实例

        Returns:
            策略ID（简化版本固定返回1）
        """
        self.strategy = strategy
        self.context = SimpleContext(self)
        strategy.context = self.context

        print(f"✅ 策略注册成功: {strategy.name}")
        return 1

    def run(self) -> BacktestResult:
        """
        运行回测

        Returns:
            回测结果
        """
        if self.strategy is None:
            raise ValueError("请先注册策略")

        if not self.bars:
            raise ValueError("请先加载K线数据")

        print(f"\n🚀 开始回测...")

        # 触发策略初始化回调
        if hasattr(self.strategy, 'on_init'):
            self.strategy.on_init(self.context)

        # 回测主循环
        for i, bar in enumerate(self.bars):
            self.current_bar = bar
            self.current_bar_index = i

            # 触发策略on_bar回调
            try:
                order = self.strategy.on_bar(self.context)

                # 处理订单
                if order:
                    self._process_order(order, bar)
            except Exception as e:
                print(f"❌ 策略执行异常 (bar {i}): {e}")

            # 更新净值
            total_asset = self._get_total_asset(bar)
            self.equity_curve.append(total_asset)

            if i % 100 == 0:
                print(f"   进度: {i}/{len(self.bars)} ({i/len(self.bars)*100:.1f}%)")

        # 触发策略on_end回调
        if hasattr(self.strategy, 'on_end'):
            self.strategy.on_end(self.context)

        print(f"✅ 回测完成")

        # 计算绩效指标
        result = self._calculate_metrics()
        return result

    def _generate_order_id(self) -> str:
        """生成订单ID"""
        self._order_counter += 1
        return f"order_{self._order_counter:06d}"

    def _add_order(self, order: Dict) -> None:
        """添加订单"""
        self.pending_orders.append(order)
        self.orders.append(order)

    def _cancel_order(self, order_id: str) -> None:
        """撤销订单"""
        for i, order in enumerate(self.pending_orders):
            if order['order_id'] == order_id and order['status'] == 'pending':
                order['status'] = 'cancelled'
                self.pending_orders.pop(i)
                print(f"   🗑️  订单已撤销: {order_id}")
                return

    def _process_order(self, order: Dict, bar: Dict) -> None:
        """
        处理订单

        简化版：直接以bar的close价格成交
        TODO: 实现更复杂的撮合逻辑
        """
        # 生成订单ID（如果策略没有提供）
        if 'order_id' not in order:
            order['order_id'] = self._generate_order_id()

        order_id = order['order_id']
        action = order['action']
        symbol = order['symbol']
        quantity = order['quantity']
        price = order['price']

        # 添加手续费和滑点
        if action == 'buy':
            final_price = price * (1 + self.slippage_rate)
            cost = final_price * quantity * (1 + self.commission_rate)

            if self.cash >= cost:
                # 执行买入
                self.cash -= cost
                self.positions[symbol] = self.positions.get(symbol, 0) + quantity

                # 记录成交
                trade = {
                    'trade_id': f"trade_{len(self.trades)+1:06d}",
                    'order_id': order_id,
                    'symbol': symbol,
                    'action': 'buy',
                    'price': final_price,
                    'quantity': quantity,
                    'commission': final_price * quantity * self.commission_rate,
                    'time': bar['trade_date']
                }
                self.trades.append(trade)

                order['status'] = 'filled'
                print(f"   ✅ 买入成交: {symbol} {quantity}股 @ {final_price:.2f}")
            else:
                order['status'] = 'rejected'
                print(f"   ❌ 买入失败: 资金不足")

        elif action == 'sell':
            current_position = self.positions.get(symbol, 0)
            sell_quantity = abs(quantity)  # 确保是正数

            if current_position >= sell_quantity:
                # 执行卖出
                final_price = price * (1 - self.slippage_rate)
                revenue = final_price * sell_quantity * (1 - self.commission_rate)

                # 计算成本（假设持仓成本不变）
                avg_cost = self._get_avg_cost(symbol)
                cost_price = avg_cost if avg_cost > 0 else final_price
                cost_value = cost_price * sell_quantity
                profit = revenue - cost_value

                self.cash += revenue
                self.positions[symbol] = current_position - sell_quantity

                # 清零持仓
                if self.positions[symbol] == 0:
                    del self.positions[symbol]

                # 记录成交
                trade = {
                    'trade_id': f"trade_{len(self.trades)+1:06d}",
                    'order_id': order_id,
                    'symbol': symbol,
                    'action': 'sell',
                    'price': final_price,
                    'quantity': sell_quantity,
                    'commission': final_price * sell_quantity * self.commission_rate,
                    'profit': profit,
                    'profit_pct': profit / cost_value if cost_value > 0 else 0,
                    'time': bar['trade_date']
                }
                self.trades.append(trade)

                order['status'] = 'filled'
                print(f"   ✅ 卖出成交: {symbol} {sell_quantity}股 @ {final_price:.2f}, 盈亏: {profit:.2f}")
            else:
                order['status'] = 'rejected'
                print(f"   ❌ 卖出失败: 持仓不足 (持有{current_position}, 想卖{sell_quantity})")

    def _get_avg_cost(self, symbol: str) -> float:
        """获取持仓成本价（简化版）"""
        # 简化处理：假设成本价等于买入时的平均价
        # TODO: 实现更精确的成本价计算
        buy_trades = [t for t in self.trades if t['symbol'] == symbol and t['action'] == 'buy']
        sell_trades = [t for t in self.trades if t['symbol'] == symbol and t['action'] == 'sell']

        total_cost = sum(t['price'] * t['quantity'] for t in buy_trades)
        total_sell = sum(t['price'] * t['quantity'] for t in sell_trades)

        current_quantity = self.positions.get(symbol, 0)
        if current_quantity > 0:
            return (total_cost - total_sell) / current_quantity

        return 0.0

    def _get_total_asset(self, bar: Dict = None) -> float:
        """计算总资产（现金+持仓市值）"""
        total = self.cash

        if bar:
            # 使用当前bar的价格计算持仓市值
            for symbol, quantity in self.positions.items():
                market_price = bar.get('close', 0)
                total += market_price * quantity

        return total

    def _calculate_metrics(self) -> BacktestResult:
        """
        计算绩效指标

        Returns:
            回测结果
        """
        result = BacktestResult()

        # 基础指标
        final_asset = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        result.total_return = (final_asset - self.initial_capital) / self.initial_capital

        # 年化收益率
        if len(self.equity_curve) > 1:
            # 假设一年252个交易日
            days = len(self.equity_curve)
            years = days / 252.0
            if years > 0:
                result.annual_return = ((1 + result.total_return) ** (1 / years)) - 1

        # 净值曲线
        result.equity_curve = self.equity_curve

        # 交易记录
        result.trades = self.trades
        result.total_trades = len(self.trades)

        # 计算收益率序列
        returns = np.diff(np.array(self.equity_curve)) / np.array(self.equity_curve[:-1])

        # 夏普比率（假设无风险利率为3%）
        if len(returns) > 1:
            rf = 0.03 / 252  # 日无风险利率
            excess_returns = returns - rf
            if np.std(excess_returns) > 0:
                result.sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

        # 最大回撤
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        result.max_drawdown = np.min(drawdown)
        result.drawdowns = drawdown.tolist()

        # 胜率
        if result.total_trades > 0:
            profit_trades = [t for t in self.trades if t.get('profit', 0) > 0]
            result.win_rate = len(profit_trades) / result.total_trades

            # 平均每笔收益
            total_profit = sum(t.get('profit', 0) for t in self.trades)
            result.avg_profit_per_trade = total_profit / result.total_trades

            # 盈亏比
            total_profit_abs = sum(abs(t.get('profit', 0)) for t in profit_trades)
            loss_trades = [t for t in self.trades if t.get('profit', 0) < 0]
            total_loss_abs = sum(abs(t.get('profit', 0)) for t in loss_trades) if loss_trades else 0.0001

            result.profit_loss_ratio = total_profit_abs / total_loss_abs if total_loss_abs > 0 else 0

        return result
