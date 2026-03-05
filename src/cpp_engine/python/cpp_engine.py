"""
C++回测引擎的Python包装类

提供与python_engine.py兼容的接口
"""

import sys
from typing import List, Dict, Optional, Callable
from pathlib import Path

# 尝试导入编译好的C++模块
import os
module_loaded = False

# 尝试从build目录导入
build_path = os.path.join(os.path.dirname(__file__), '..', 'build')
if build_path not in sys.path:
    sys.path.insert(0, build_path)

try:
    import cpp_engine as _cpp_engine_module
    _CppEngine = _cpp_engine_module.SimpleCppEngine
    BacktestResult = _cpp_engine_module.BacktestResult
    module_loaded = True
except ImportError as e:
    print(f"⚠️  C++引擎导入失败: {e}")
    print("请确保已编译C++引擎:")
    print("   cd src/cpp_engine/build")
    print("   cmake .. && make")
    sys.exit(1)


class CppBacktestEngine:
    """
    C++回测引擎的Python包装类

    兼容现有PythonBacktestEngine接口
    """

    def __init__(self,
                 initial_capital: float = 1000000.0,
                 commission_rate: float = 0.0003,
                 slippage_rate: float = 0.0001):
        """
        初始化C++回测引擎

        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率（默认0.03%）
            slippage_rate: 滑点率（暂未实现）
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        # 创建C++引擎实例
        self._engine = _CppEngine(initial_capital, commission_rate)

        # 状态变量（保持兼容性）
        self.cash = initial_capital
        self.positions: Dict[str, int] = {}
        self.bars: List[Dict] = []
        self.current_bar_index = 0
        self.current_bar: Dict = {}

        # 策略实例
        self.strategy = None

    def init(self, bars: List[Dict]) -> None:
        """
        初始化回测

        Args:
            bars: K线数据列表，每个元素是dict格式
        """
        self.bars = bars

        # 转换数据格式为C++需要的格式
        # C++期望: list of (date_str, dict) tuples
        bars_data = []
        for bar in bars:
            date_str = bar.get('trade_date', '')

            # 提取数值字段
            data = {
                'open': float(bar.get('open', 0)),
                'high': float(bar.get('high', 0)),
                'low': float(bar.get('low', 0)),
                'close': float(bar.get('close', 0)),
                'vol': float(bar.get('vol', 0)),
                'amount': float(bar.get('amount', 0))
            }
            bars_data.append((date_str, data))

        # 加载到C++引擎
        self._engine.load_data(bars_data)

        print(f"✅ C++回测引擎初始化完成")
        print(f"   - 初始资金: {self.initial_capital:,.2f}")
        print(f"   - K线数量: {len(bars)}")
        if bars:
            print(f"   - 时间范围: {bars[0]['trade_date']} ~ {bars[-1]['trade_date']}")

    def register_strategy(self, strategy) -> int:
        """
        注册策略

        Args:
            strategy: 策略实例，必须实现on_bar方法

        Returns:
            策略ID
        """
        self.strategy = strategy
        print(f"✅ 策略注册成功: {strategy.__class__.__name__}")
        return 1

    def run_backtest(self) -> BacktestResult:
        """
        运行回测

        Returns:
            回测结果
        """
        if not self.strategy:
            raise ValueError("未注册策略，请先调用register_strategy()")

        # 切换到项目根目录，确保C++引擎的相对路径正确
        import os
        original_cwd = os.getcwd()
        # 从当前文件位置推导项目根目录（src/cpp_engine/python -> 项目根目录）
        # cpp_engine.py: src/cpp_engine/python/cpp_engine.py
        # 需要向上4级: python/ -> cpp_engine/ -> src/ -> Multi_Agent_Quant_Trader/
        project_root = Path(__file__).parent.parent.parent.parent
        os.chdir(project_root)

        try:
            print(f"\n🚀 开始C++回测...")

            # 定义策略回调函数
            def strategy_callback(context):
                """C++引擎调用Python策略的回调函数"""
                # 更新引擎状态（用于兼容）
                self.cash = context.get_cash()
                # positions需要从C++查询

                try:
                    # 调用Python策略
                    order = self.strategy.on_bar(context)

                    # 如果策略返回订单，执行
                    if order:
                        symbol = order.get('symbol', '')
                        action = order.get('action', '')
                        quantity = order.get('quantity', 0)
                        price = order.get('price', 0)

                        if action == 'buy':
                            context.buy(symbol, quantity, price)
                        elif action == 'sell':
                            context.sell(symbol, quantity, price)

                except Exception as e:
                    # 捕获策略异常，防止C++崩溃
                    print(f"策略异常: {e}")
                    return

            # 运行C++引擎
            self._engine.run(strategy_callback)

            # 获取结果
            result = self._engine.get_results()

            print(f"✅ C++回测完成")
            print(f"   - 总收益率: {result.total_return:.2%}")
            print(f"   - 交易次数: {result.total_trades}")
            print(f"   - 夏普比率: {result.sharpe_ratio:.2f}")
            print(f"   - 最大回撤: {result.max_drawdown:.2%}")

            return result
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)

    def _generate_order_id(self) -> str:
        """生成订单ID（兼容性方法）"""
        import time
        return f"order_{int(time.time() * 1000000)}"


# ========== 便捷函数 ==========

def create_engine(initial_capital: float = 1000000.0,
                 commission_rate: float = 0.0003) -> CppBacktestEngine:
    """
    创建C++回测引擎

    Args:
        initial_capital: 初始资金
        commission_rate: 手续费率

    Returns:
        CppBacktestEngine实例
    """
    return CppBacktestEngine(initial_capital, commission_rate)


def run_quick_backtest(bars: List[Dict],
                      strategy_class,
                      strategy_params: Dict = None) -> BacktestResult:
    """
    快速回测（便捷函数）

    Args:
        bars: K线数据
        strategy_class: 策略类
        strategy_params: 策略参数

    Returns:
        回测结果
    """
    engine = create_engine()
    engine.init(bars)

    # 创建策略实例
    if strategy_params:
        strategy = strategy_class(**strategy_params)
    else:
        strategy = strategy_class()

    engine.register_strategy(strategy)
    result = engine.run_backtest()

    return result
