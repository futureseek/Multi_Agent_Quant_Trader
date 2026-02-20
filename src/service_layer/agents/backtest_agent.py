"""
BacktestAgent - 回测执行Agent

负责执行回测、计算绩效指标
"""

from typing import Dict, Any, Optional, List

from ..strategy import PythonBacktestEngine, BacktestResult


class BacktestAgent:
    """
    回测Agent

    职责：
    - 加载策略代码
    - 执行回测
    - 计算绩效指标
    - 返回格式化结果
    """

    def __init__(self):
        """初始化BacktestAgent"""
        self.name = "backtest_agent"
        self.engine = None
        self.strategy = None
        print(f"✅ BacktestAgent 初始化完成")

    def run_backtest(self,
                    strategy_code: str,
                    data: List[Dict],
                    initial_capital: float = 1000000.0,
                    commission_rate: float = 0.0003,
                    slippage_rate: float = 0.0001) -> Dict[str, Any]:
        """
        执行回测

        Args:
            strategy_code: 策略Python代码
            data: K线数据列表
            initial_capital: 初始资金（默认100万）
            commission_rate: 手续费率（默认0.03%）
            slippage_rate: 滑点率（默认0.01%）

        Returns:
            {
                "success": True/False,
                "result": BacktestResult.to_dict(),
                "summary": "回测结果摘要",
                "error": "错误信息"
            }
        """
        try:
            print(f"\n⚙️  开始执行回测...")
            print(f"📊 数据量: {len(data)} 根K线")

            # ========== 步骤1: 加载策略代码 ==========
            strategy = self._load_strategy_from_code(strategy_code)
            if strategy is None:
                return {
                    "success": False,
                    "error": "策略代码加载失败"
                }

            print("✅ 策略代码加载完成")

            # ========== 步骤2: 创建回测引擎 ==========
            self.engine = PythonBacktestEngine(
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage_rate=slippage_rate
            )

            # ========== 步骤3: 注册并初始化 ==========
            self.engine.register_strategy(strategy)
            self.engine.init(data)

            print("✅ 回测引擎初始化完成")

            # ========== 步骤4: 执行回测 ==========
            result = self.engine.run()

            # ========== 步骤5: 格式化结果 ==========
            summary = self._format_summary(result)

            print(f"✅ 回测执行完成")
            print(f"\n{summary}")

            return {
                "success": True,
                "result": result.to_dict(),
                "summary": summary
            }

        except Exception as e:
            print(f"❌ 回测执行失败: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"回测执行失败: {str(e)}"
            }

    def _load_strategy_from_code(self, code: str) -> Optional[object]:
        """
        从代码字符串加载策略类

        Args:
            code: 策略Python代码

        Returns:
            策略实例，如果加载失败返回None
        """
        try:
            # 导入必要的基类和类型
            from ..strategy.strategy_base import StrategyBase
            from typing import Dict, Any, Optional, List

            # 创建命名空间，预先注入常用类型
            namespace = {
                "StrategyBase": StrategyBase,
                "Dict": Dict,
                "Any": Any,
                "Optional": Optional,
                "List": List,
                "__builtins__": __builtins__
            }

            # 执行代码
            exec(code, namespace)

            # 查找策略类
            strategy_class = None
            for key, value in namespace.items():
                if isinstance(value, type) and issubclass(value, StrategyBase) and value is not StrategyBase:
                    strategy_class = value
                    break

            if strategy_class is None:
                print("❌ 未找到策略类，代码可能不符合StrategyBase接口")
                return None

            # 创建策略实例
            strategy = strategy_class()

            # 验证必要方法
            if not hasattr(strategy, 'on_bar'):
                print("❌ 策略类缺少on_bar方法")
                return None

            print(f"✅ 成功加载策略类: {strategy.__class__.__name__}")
            return strategy

        except Exception as e:
            print(f"❌ 策略代码加载失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _format_summary(self, result: BacktestResult) -> str:
        """
        格式化回测结果摘要
        """
        return f"""
=== 回测结果 ===
📈 总收益率: {result.total_return:.2%}
📅 年化收益率: {result.annual_return:.2%}
⚡ 夏普比率: {result.sharpe_ratio:.2f}
📉 最大回撤: {result.max_drawdown:.2%}
🎯 胜率: {result.win_rate:.2%}
💹 交易次数: {result.total_trades}
💰 平均每笔收益: {result.avg_profit_per_trade:.2f}
📊 盈亏比: {result.profit_loss_ratio:.2f}
==================
"""


# 全局BacktestAgent实例
backtest_agent = BacktestAgent()
