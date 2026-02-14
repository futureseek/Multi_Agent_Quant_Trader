"""
Strategy模块

提供策略基类、回测引擎和示例策略
"""

from .strategy_base import StrategyBase, BacktestResult
from .simple_context import SimpleContext
from .python_engine import PythonBacktestEngine

__all__ = [
    'StrategyBase',
    'BacktestResult',
    'SimpleContext',
    'PythonBacktestEngine'
]
