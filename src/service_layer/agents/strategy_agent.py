"""
StrategyAgent - 策略生成Agent

使用LLM根据用户需求生成交易策略代码
"""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..config.config_manager import config_manager


class StrategyAgent:
    """
    策略生成Agent

    职责：
    - 根据用户需求生成策略代码
    - 支持多种策略类型（均线、RSI、MACD等）
    - 生成符合StrategyBase接口的代码
    """

    def __init__(self):
        """初始化StrategyAgent"""
        self.name = "strategy_agent"

        # 获取配置
        agent_config = config_manager.get_model_config(self.name)
        self.llm = ChatOpenAI(
            model=agent_config["model_name"],
            openai_api_key=agent_config["api_key"],
            openai_api_base=agent_config["base_url"],
            temperature=0.3,  # 策略生成需要稳定
            max_tokens=2000
        )

        print(f"✅ StrategyAgent 初始化完成 - 模型: {agent_config['model_name']}")

    async def generate_strategy(self,
                                user_request: str,
                                data_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        生成策略代码

        Args:
            user_request: 用户需求描述
            data_context: 数据上下文（可选，包含股票信息、市场数据等）

        Returns:
            {
                "success": True/False,
                "strategy_code": "策略Python代码",
                "strategy_name": "策略类名",
                "description": "策略描述",
                "error": "错误信息"（如果失败）
            }
        """
        try:
            print(f"\n🤖 生成交易策略...")
            print(f"📋 用户需求: {user_request}")

            # 验证输入
            if not user_request or user_request.strip() == "":
                return {
                    "success": False,
                    "error": "用户需求不能为空"
                }

            # 构建提示词
            prompt = self._build_strategy_prompt(user_request, data_context)

            # 调用LLM生成
            print("🚀 开始调用LLM...")
            response = await self.llm.ainvoke([
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ])

            strategy_code = response.content.strip()

            # 提取代码（去除markdown标记）
            if "```python" in strategy_code:
                strategy_code = strategy_code.split("```python")[1].split("```")[0].strip()

            # 验证代码
            code_summary = self._validate_code(strategy_code)

            print(f"✅ 策略代码生成完成")
            print(f"📊 代码长度: {len(strategy_code)}字符")
            print(f"💭 代码预览:\n{code_summary[:200]}...")

            return {
                "success": True,
                "strategy_code": strategy_code,
                "strategy_name": self._extract_class_name(strategy_code),
                "description": f"根据需求生成的策略: {user_request[:50]}..."
            }

        except Exception as e:
            print(f"❌ 策略生成失败: {e}")
            return {
                "success": False,
                "error": f"策略生成失败: {str(e)}"
            }

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """
你是一个专业的量化策略设计师。请根据用户的需求生成Python交易策略代码。

策略代码要求：
1. 必须继承自StrategyBase类
2. 必须实现on_bar(self, context)方法
3. 使用context对象访问数据和下单：
   - context.get_bar(symbol, field, offset): 获取单根K线
   - context.get_series(symbol, field, count): 获取序列数据
   - context.buy(symbol, quantity, price): 下买单
   - context.sell(symbol, quantity, price): 下卖单
   - context.get_cash(): 获取可用资金
   - context.get_position(symbol): 获取持仓
4. 策略逻辑清晰，有适当注释
5. 处理边界情况（数据不足返回None）

策略类型参考：
- 均线策略：MA、EMA、双均线金叉死叉
- 动量指标：RSI、MACD、KDJ
- 价格形态：突破、反转、形态识别
- 量价策略：成交量突破、缩量上涨

只输出Python代码，不要markdown标记，不要任何文字说明。
"""

    def _build_strategy_prompt(self, user_request: str, data_context: Optional[Dict]) -> str:
        """构建策略生成提示词"""

        prompt = f"""
用户需求: {user_request}
"""

        # 如果有数据上下文，添加到prompt
        if data_context:
            # 提取数据字段信息
            extracted_data = data_context.get("extracted_data", {})
            data_list = extracted_data.get("data", [])

            if data_list:
                # 从第一条数据中提取字段
                available_fields = list(data_list[0].keys())

                prompt += f"""

可用数据字段: {', '.join(available_fields)}

⚠️ 重要字段说明:
- close: 收盘价
- open: 开盘价
- high: 最高价
- low: 最低价
- vol: 成交量（注意是vol不是volume）
- amount: 成交额
- trade_date: 交易日期

请只使用上述字段访问数据，不要使用其他字段名。
"""

            # 添加股票信息
            stock_info = data_context.get("stock_info", {})
            if stock_info:
                prompt += f"""

股票信息:
- 代码: {stock_info.get('code', 'N/A')}
- 名称: {stock_info.get('name', 'N/A')}
- 时间范围: {data_context.get('date_range', 'N/A')}
"""

        prompt += """

请生成对应的交易策略代码。策略应该清晰、可执行、有良好的注释。

示例格式（均线金叉策略）:
```python
from src.service_layer.strategy.strategy_base import StrategyBase
from typing import Dict, Optional

class MAStrategy(StrategyBase):
    \"\"\"双均线策略：短期均线上穿长期均线买入，下穿卖出\"\"\"
    
    def __init__(self, short=5, long=20):
        super().__init__()
        self.short = short
        self.long = long
        self.prev_short_ma = None
        self.prev_long_ma = None

    def on_bar(self, context):
        # 获取当前股票代码 (可根据用户需求调整)
        symbol = '600000.SH'
        
        try:
            # 获取当前价格
            current_price = context.get_bar(symbol, 'close', 0)
            
            # 获取短期和长期均线数据
            short_series = context.get_series(symbol, 'close', self.short)
            long_series = context.get_series(symbol, 'close', self.long)
            
            # 数据不足时跳过
            if len(short_series) < self.short or len(long_series) < self.long:
                return None
                
            # 计算均线值
            short_ma = sum(short_series) / len(short_series)
            long_ma = sum(long_series) / len(long_series)
            
            # 金叉买入信号
            if (self.prev_short_ma is not None and 
                self.prev_long_ma is not None and
                self.prev_short_ma <= self.prev_long_ma and 
                short_ma > long_ma and 
                context.get_cash() > 0):
                
                # 计算买入量 (使用可用资金的90%)
                cash = context.get_cash()
                quantity = int(cash * 0.9 / current_price / 100) * 100  # 整百股
                
                if quantity >= 100:
                    order = {
                        'action': 'buy',
                        'symbol': symbol,
                        'quantity': quantity,
                        'price': current_price
                    }
                    self.prev_short_ma = short_ma
                    self.prev_long_ma = long_ma
                    return order
            
            # 死叉卖出信号
            elif (self.prev_short_ma is not None and 
                  self.prev_long_ma is not None and
                  self.prev_short_ma >= self.prev_long_ma and 
                  short_ma < long_ma and 
                  context.get_position(symbol) > 0):
                
                # 卖出全部持仓
                position = context.get_position(symbol)
                order = {
                    'action': 'sell',
                    'symbol': symbol,
                    'quantity': -position,
                    'price': current_price
                }
                self.prev_short_ma = short_ma
                self.prev_long_ma = long_ma
                return order
            
            # 更新前一根K线的均线值
            self.prev_short_ma = short_ma
            self.prev_long_ma = long_ma
            
        except (IndexError, KeyError):
            # 数据异常时跳过
            return None
            
        return None
```

请严格按照这个格式生成代码，必须包含：
1. 正确的import语句
2. 继承StrategyBase的类定义  
3. 完整的on_bar方法实现
4. 适当的错误处理和边界条件检查
5. 合理的交易逻辑
"""

        return prompt

    def _validate_code(self, code: str) -> str:
        """验证策略代码"""
        lines = code.split('\n')
        summary = []

        # 检查关键元素
        if 'class ' in code:
            class_name = [line for line in lines if 'class' in line][0]
            summary.append(f"✅ 策略类: {class_name}")

        if 'def on_bar' in code:
            summary.append("✅ 实现了on_bar方法")

        if 'context.buy' in code or 'context.sell' in code:
            summary.append("✅ 使用了交易接口")

        return '\n'.join(summary)

    def _extract_class_name(self, code: str) -> str:
        """从代码中提取类名"""
        import re
        match = re.search(r'class\s+(\w+)', code)
        return match.group(1) if match else "GeneratedStrategy"


# 全局StrategyAgent实例
strategy_agent = StrategyAgent()
