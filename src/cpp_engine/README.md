# C++回测引擎 (src/cpp_engine)

高性能C++回测引擎，用于Multi-Agent Quant Trader项目。

## 🎯 特性

- ✅ C++核心引擎，性能优于纯Python实现（约4倍）
- ✅ pybind11桥接，Python策略无缝调用
- ✅ 兼容现有Python引擎接口
- ✅ 支持双均线等经典CTA策略
- ✅ 市价单、手续费、持仓管理
- ✅ **已集成到系统，完全替换Python引擎**

## 📁 目录结构

```
src/cpp_engine/
├── include/           # C++头文件
│   ├── bar.h         # K线数据结构
│   ├── context.h     # 策略上下文接口
│   └── engine.h      # 核心引擎
├── src/              # C++源文件
│   ├── context.cpp
│   ├── engine.cpp
│   └── python_bindings.cpp  # pybind11绑定
├── python/           # Python包装层
│   └── cpp_engine.py
├── tests/            # 测试脚本
│   ├── test_cpp_engine.py
│   ├── test_cta_strategies.py
│   └── CTA_TEST_REPORT.md
├── build/            # 编译输出目录
├── CMakeLists.txt    # 构建配置
└── README.md
```

## 🔧 编译要求

- C++17编译器（GCC 7+, Clang 5+, MSVC 2017+）
- CMake 3.15+
- Python 3.10+
- pybind11

### 安装依赖

```bash
# Ubuntu/Debian
sudo apt-get install cmake build-essential python3-dev

# 安装pybind11
pip install pybind11
```

## 🚀 编译步骤

```bash
cd src/cpp_engine
mkdir -p build && cd build
cmake ..
make
```

编译成功后，会在`build`目录生成`cpp_engine.cpython-310-x86_64-linux-gnu.so`文件。

## 📖 使用方法

### 基本使用

```python
from cpp_core.python.cpp_engine import CppBacktestEngine

# 创建引擎
engine = CppBacktestEngine(
    initial_capital=1000000.0,
    commission_rate=0.0003
)

# 加载数据
bars = [
    {
        'trade_date': '20240101',
        'open': 10.5,
        'high': 10.8,
        'low': 10.3,
        'close': 10.7,
        'vol': 1000000,
        'amount': 10700000.0
    },
    # ... 更多K线数据
]
engine.init(bars)

# 创建策略
class MyStrategy:
    def __init__(self):
        self.prev_ma = None

    def on_bar(self, context):
        # 获取历史数据
        closes = context.get_series('close', 20)

        # 计算均线
        ma20 = sum(closes) / len(closes)

        # 获取当前价格
        current_price = context.get_bar('close', 0)

        # 交易逻辑
        if self.prev_ma is not None:
            if self.prev_ma < current_price and ma20 > current_price:
                return {
                    'action': 'buy',
                    'symbol': 'TEST',
                    'quantity': 100,
                    'price': current_price
                }

        self.prev_ma = ma20
        return None

# 注册并运行
strategy = MyStrategy()
engine.register_strategy(strategy)
result = engine.run_backtest()

# 查看结果
print(f"总收益率: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

## 🧪 测试

### 快速测试

```bash
# 从项目根目录运行
conda run -n MAtrader python src/cpp_engine/tests/test_cpp_engine.py
```

### CTA策略全面测试

```bash
# 测试6个经典CTA策略的兼容性
conda run -n MAtrader python src/cpp_engine/tests/test_cta_strategies.py
```

测试包含：
1. 基本功能测试（双均线策略）
2. 接口兼容性测试
3. 性能测试
4. **CTA策略测试套件**:
   - 双均线策略 (MA Cross)
   - MACD策略
   - 布林带策略 (Bollinger Bands)
   - 动量策略 (Momentum)
   - RSI策略
   - 通道突破策略 (Channel Breakout)

### 测试结果

**最新测试报告**: [CTA_TEST_REPORT.md](tests/CTA_TEST_REPORT.md)

| 指标 | 结果 |
|------|------|
| 策略运行成功率 | 83.3% (5/6) |
| 平均执行速度 | 20,137 bars/sec |
| 接口兼容性 | 100% |
| 异常崩溃 | 0次 |

详细测试结果请查看: `cpp_core/tests/CTA_TEST_REPORT.md`

## 📊 性能对比

预期性能提升：**3-5倍**快于纯Python实现

| 数据量 | Python引擎 | C++引擎 | 加速比 |
|--------|-----------|---------|--------|
| 1,000根 | ~0.5s | ~0.1s | 5x |
| 10,000根 | ~5s | ~1s | 5x |

## 🔍 Context接口

策略可用的Context方法：

```python
# 数据访问
context.get_series(field, count)  # 获取历史序列
context.get_bar(field, offset)    # 获取单个值
context.get_current_date()        # 获取当前日期

# 交易接口
context.buy(symbol, quantity, price)   # 买入
context.sell(symbol, quantity, price)  # 卖出

# 查询接口
context.get_cash()              # 可用资金
context.get_position(symbol)    # 持仓数量
```

## ⚠️ 注意事项

1. **字段名约定**：Tushare数据使用`vol`而非`volume`
2. **数据格式**：确保trade_date为YYYYMMDD格式字符串
3. **异常处理**：策略异常会被捕获，不会导致C++崩溃

## 📝 开发计划

- [x] MVP基本功能
- [ ] 增加订单类型（限价单、止损单）
- [ ] 多股票组合支持
- [ ] 更详细的性能指标
- [ ] 与Python引擎结果对比验证

## 🐛 已知问题

- 滑点模型尚未实现
- 仅支持单股票回测
- 胜率计算简化（未配对买卖）

## 📧 联系方式

如有问题，请提issue或联系开发团队。
