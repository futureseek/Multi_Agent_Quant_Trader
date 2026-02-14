"""
策略基类 - 所有用户策略必须继承此类

策略开发指南：
1. 继承StrategyBase类
2. 实现on_bar(self, context)方法
3. 通过context对象访问数据和执行交易
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List


class StrategyBase(ABC):
    """
    策略基类

    用户编写策略时继承此类并实现on_bar方法
    """

    def __init__(self):
        """初始化策略"""
        self.name = self.__class__.__name__
        self.context = None  # 上下文对象，回测时由引擎注入

    def on_init(self, context: 'SimpleContext') -> None:
        """
        策略初始化回调

        在回测开始前调用一次，可用于：
        - 初始化指标计算器
        - 设置策略参数
        - 预加载必要数据

        Args:
            context: 上下文对象
        """
        pass

    @abstractmethod
    def on_bar(self, context: 'SimpleContext') -> Optional[Dict]:
        """
        每根K线回调（核心方法）

        Args:
            context: 上下文对象，提供数据访问和交易接口

        Returns:
            订单字典或None，格式为:
            {
                'action': 'buy' | 'sell',
                'symbol': '600000.SH',
                'quantity': 100,
                'price': 10.5
            }
            如果返回None，表示不交易
        """
        pass

    def on_order(self, context: 'SimpleContext', order: Dict) -> None:
        """
        订单状态回调

        当订单状态发生变化时触发（成交、拒绝、撤销等）

        Args:
            context: 上下文对象
            order: 订单信息字典
        """
        pass

    def on_trade(self, context: 'SimpleContext', trade: Dict) -> None:
        """
        成交回调

        当订单成交时触发

        Args:
            context: 上下文对象
            trade: 成交信息字典
        """
        pass

    def on_end(self, context: 'SimpleContext') -> None:
        """
        回测结束回调

        在回测结束后调用一次，可用于：
        - 生成策略分析报告
        - 记录策略日志
        - 释放资源

        Args:
            context: 上下文对象
        """
        pass


class BacktestResult:
    """
    回测结果类

    包含回测的所有性能指标和统计数据
    """

    def __init__(self):
        self.total_return: float = 0.0           # 总收益率
        self.annual_return: float = 0.0          # 年化收益率
        self.sharpe_ratio: float = 0.0          # 夏普比率
        self.max_drawdown: float = 0.0          # 最大回撤
        self.win_rate: float = 0.0              # 胜率
        self.total_trades: int = 0              # 总交易次数
        self.avg_profit_per_trade: float = 0.0   # 平均每笔收益
        self.profit_loss_ratio: float = 0.0      # 盈亏比

        self.equity_curve: List[float] = []      # 净值曲线
        self.trades: List[Dict] = []           # 交易记录
        self.drawdowns: List[float] = []         # 回撤序列

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'avg_profit_per_trade': self.avg_profit_per_trade,
            'profit_loss_ratio': self.profit_loss_ratio,
            'equity_curve': self.equity_curve,
            'trades': self.trades,
            'drawdowns': self.drawdowns
        }

    def summary(self) -> str:
        """生成摘要文本"""
        return f"""
=== 回测结果摘要 ===
总收益率: {self.total_return:.2%}
年化收益率: {self.annual_return:.2%}
夏普比率: {self.sharpe_ratio:.2f}
最大回撤: {self.max_drawdown:.2%}
胜率: {self.win_rate:.2%}
交易次数: {self.total_trades}
平均每笔收益: {self.avg_profit_per_trade:.2f}
盈亏比: {self.profit_loss_ratio:.2f}
==================
"""
