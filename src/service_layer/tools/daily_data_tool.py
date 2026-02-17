"""
DailyDataTool - 日K线数据获取工具
提供股票日线行情数据获取功能
"""

import pandas as pd
import tushare as ts
import os
from typing import Dict, Optional, Any
from langchain_core.tools import tool
from datetime import datetime, timedelta
from ..config.config_manager import config_manager


class DailyDataTool:
    """日K线数据工具类"""

    def __init__(self):
        """
        初始化日K线数据工具
        从配置文件读取Tushare API token
        """
        try:
            # 从配置文件读取Tushare API token
            self.token = config_manager.get_tushare_config()
            if self.token:
                ts.set_token(self.token)
                self.pro = ts.pro_api()
                print(f"✅ Tushare API 初始化成功")
            else:
                self.pro = None
                print(f"⚠️  未找到Tushare API token，将使用模拟数据")
        except Exception as e:
            self.pro = None
            print(f"⚠️ Tushare API 初始化失败: {e}，将使用模拟数据")

    def _validate_stock_code(self, ts_code: str) -> str:
        """
        验证和标准化股票代码

        Args:
            ts_code: 股票代码

        Returns:
            标准化的股票代码
        """
        if not ts_code:
            raise ValueError("股票代码不能为空")

        # 移除空格并转换为大写
        ts_code = ts_code.strip().upper()

        # 如果没有交易所后缀，根据代码规则自动添加
        if '.' not in ts_code:
            if ts_code.startswith(('60', '68', '90')):
                ts_code += '.SH'  # 上交所
            elif ts_code.startswith(('00', '30', '20')):
                ts_code += '.SZ'  # 深交所
            else:
                raise ValueError(f"无法识别股票代码: {ts_code}")

        return ts_code

    def _validate_date_format(self, date_str: str) -> str:
        """
        验证日期格式

        Args:
            date_str: 日期字符串

        Returns:
            格式化的日期字符串(YYYYMMDD)
        """
        if not date_str:
            return ""

        # 移除常见分隔符
        date_str = date_str.replace('-', '').replace('/', '').replace('.', '')

        # 验证长度
        if len(date_str) != 8:
            raise ValueError(f"日期格式错误，应为YYYYMMDD格式: {date_str}")

        # 验证是否为有效日期
        try:
            datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            raise ValueError(f"无效日期: {date_str}")

        return date_str

    def get_daily_data(self,
                      ts_code: str,
                      start_date: str = None,
                      end_date: str = None,
                      limit: int = 1000) -> Dict[str, Any]:
        """
        获取股票日线数据

        Args:
            ts_code: 股票代码(如000001.SZ)
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            limit: 最大记录数

        Returns:
            包含股票日线数据的字典
        """
        try:
            print(f"📊 开始获取股票 {ts_code} 的日线数据...")

            # 验证参数
            ts_code = self._validate_stock_code(ts_code)

            # 处理日期参数
            if start_date:
                start_date = self._validate_date_format(start_date)
            if end_date:
                end_date = self._validate_date_format(end_date)
            else:
                # 如果没有指定结束日期，使用今天
                end_date = datetime.now().strftime('%Y%m%d')

            # 如果没有指定开始日期，默认获取最近250个交易日
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            print(f"📈 查询参数: {ts_code}, {start_date} ~ {end_date}")

            # 调用Tushare API获取数据
            if self.pro:
                try:
                    # 详细输出：用于调试和验证
                    print(f"📞 准备调用Tushare pro.daily():")
                    print(f"   ts_code: {ts_code}")
                    print(f"   start_date: {start_date}")
                    print(f"   end_date: {end_date}")

                    df = self.pro.daily(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )

                    print(f"✅ Tushare API调用成功")
                    print(f"   获取数据条数: {len(df)}")
                    print(f"   数据列: {list(df.columns)}")
                    print(f"   时间范围: {df.index[0]} ~ {df.index[-1]}")

                except Exception as api_error:
                    print(f"⚠️ Tushare API调用失败: {api_error}")
                    print(f"   错误类型: {type(api_error).__name__}")
                    df = pd.DataFrame()

            # 数据处理和验证
            if df is None or df.empty:
                return {
                    "success": False,
                    "message": f"未获取到股票 {ts_code} 的数据",
                    "data": None,
                    "count": 0
                }

            # 按日期排序
            df = df.sort_values('trade_date').reset_index(drop=True)

            # 限制返回数量
            if len(df) > limit:
                df = df.tail(limit)

            # 数据格式化
            kline_data = df.to_dict('records')

            # 🎯 保存CSV文件用于调试
            try:
                # 使用绝对路径确保目录创建成功
                import sys
                from pathlib import Path

                # 获取项目根目录（假设当前文件在 src/service_layer/tools/ 下）
                current_file = Path(__file__)
                project_root = current_file.parent.parent.parent.parent
                csv_dir = project_root / "data" / "debug_csv" / "daily_data_tool"

                # 创建目录
                csv_dir.mkdir(parents=True, exist_ok=True)

                # 生成文件名（包含时间戳避免覆盖）
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = csv_dir / f"{ts_code}_{start_date}_{end_date}_{timestamp}.csv"

                # 保存CSV
                df.to_csv(csv_filename, index=False, encoding='utf-8')

                print(f"📁 数据已保存到CSV文件: {csv_filename}")
                print(f"📊 CSV文件包含 {len(df)} 行，{len(df.columns)} 列")

                # 输出前几行数据用于验证
                print(f"📋 CSV前3行数据预览:")
                for i, row in df.head(3).iterrows():
                    print(f"   {i}: {dict(row)}")

            except Exception as csv_error:
                print(f"⚠️ CSV保存失败: {csv_error}")
                import traceback
                traceback.print_exc()

            print(f"✅ 成功处理 {len(df)} 条日线数据")

            # 统一返回格式
            return {
                "success": True,
                "message": f"成功获取 {ts_code} 的日线数据，共 {len(df)} 条记录",
                "extracted_data": {
                    "ts_code": ts_code,
                    "data_type": "daily",
                    "start_date": start_date,
                    "end_date": end_date,
                    "count": len(df),
                    "data": kline_data
                }
            }

        except Exception as e:
            error_msg = f"获取日线数据失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": None,
                "count": 0
            }


# 创建全局工具实例
daily_data_tool = DailyDataTool()


@tool
def get_daily_stock_data(ts_code: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    获取股票日线行情数据的工具函数

    Args:
        ts_code: 股票代码，如 000001.SZ 或 600000.SH
        start_date: 开始日期，格式YYYYMMDD，如 20240101
        end_date: 结束日期，格式YYYYMMDD，如 20241231

    Returns:
        字典格式的股票日线数据，包含开高低收量等信息

    Examples:
        >>> get_daily_stock_data("000001.SZ", "20240101", "20241231")
        >>> get_daily_stock_data("600000.SH")  # 获取最近一年数据
    """
    return daily_data_tool.get_daily_data(ts_code, start_date, end_date)
