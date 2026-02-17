"""
股票复权因子工具
封装Tushare的adj_factor方法，提供股票复权因子数据获取功能
"""

import pandas as pd
import tushare as ts
from typing import Optional, Dict, Any
from langchain_core.tools import tool
from datetime import datetime, timedelta

from ..config.config_manager import config_manager


def _get_tushare_pro():
    """获取Tushare Pro API实例"""
    try:
        tushare_token = config_manager.get_tushare_config()
        if not tushare_token:
            raise Exception("Tushare API token未配置")
        ts.set_token(tushare_token)
        pro = ts.pro_api()
        return pro
    except Exception as e:
        raise Exception(f"Tushare Pro API初始化失败: {str(e)}")


@tool
def get_adj_factor(
    ts_code: str = "",
    trade_date: str = "",
    start_date: str = "",
    end_date: str = ""
) -> Dict[str, Any]:
    """
    获取股票复权因子数据

    Args:
        ts_code: 股票代码，如'000001.SZ'，为空则获取所有股票
        trade_date: 交易日期，格式YYYYMMDD，如'20180718'，为空则获取指定时间范围
        start_date: 开始日期，格式YYYYMMDD，如'20180101'
        end_date: 结束日期，格式YYYYMMDD，如'20181011'

    Returns:
        包含复权因子数据的字典

    Examples:
        获取2018年7月18日复权因子: get_adj_factor('', '20180718')
        获取000001全部复权因子: get_adj_factor('000001.SZ', '')
        获取指定时间范围: get_adj_factor('000001.SZ', '', '20180101', '20181231')
    """
    try:
        print(f"🔄 开始获取复权因子 - 股票代码: {ts_code or '全部'}, 交易日期: {trade_date or '范围查询'}")

        # 验证参数逻辑
        if not ts_code and not trade_date and not (start_date and end_date):
            return {
                "success": False,
                "message": "参数不完整，需要提供以下组合之一: 1.trade_date 2.ts_code+trade_date 3.ts_code+start_date+end_date"
            }

        # 验证股票代码格式(如果提供)
        if ts_code and (len(ts_code) != 9 or '.' not in ts_code):
            return {
                "success": False,
                "message": f"股票代码格式不正确，应为'000001.SZ'格式，当前输入: {ts_code}"
            }

        # 获取Tushare Pro实例
        pro = _get_tushare_pro()

        # 构建查询参数
        params = {}
        if ts_code:
            params['ts_code'] = ts_code
        if trade_date:
            params['trade_date'] = trade_date
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        print(f"📅 查询参数: {params}")
        print(f"🔌 调用Tushare adj_factor接口...")

        df = pro.adj_factor(**params)

        if df is None or df.empty:
            return {
                "success": False,
                "message": "未获取到复权因子数据，请检查参数是否正确"
            }

        print(f"✅ 成功获取 {len(df)} 条复权因子数据")

        # 数据预处理
        df = df.sort_values(['ts_code', 'trade_date'], ascending=[True, True])

        # 保存CSV文件用于调试
        try:
            from pathlib import Path
            from datetime import datetime

            # 获取项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent
            csv_dir = project_root / "data" / "debug_csv" / "adj_factor_tool"
            csv_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名（包含adj_factor标识）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = csv_dir / f"adj_factor_{ts_code or 'multi'}_{timestamp}.csv"

            # 保存CSV
            df.to_csv(csv_filename, index=False, encoding='utf-8')
            print(f"📁 复权因子数据已保存到: {csv_filename}")

        except Exception as csv_error:
            print(f"⚠️ CSV保存失败: {csv_error}")

        # 统一返回格式
        return {
            "success": True,
            "message": f"成功获取复权因子数据，共 {len(df)} 条记录",
            "extracted_data": {
                "ts_code": ts_code or "多股票",
                "data_type": "adj_factor",
                "count": len(df),
                "data": df.to_dict('records')
            }
        }

    except Exception as e:
        error_msg = f"获取复权因子失败: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg
        }
