"""
股票日指标工具
封装Tushare的daily_basic方法，提供每日重要基本面指标数据获取功能
用于选股分析、报表展示等
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
def get_daily_basic(
    ts_code: str = "",
    trade_date: str = "",
    start_date: str = "",
    end_date: str = "",
    fields: str = ""
) -> Dict[str, Any]:
    """
    获取股票每日重要基本面指标

    Args:
        ts_code: 股票代码，如'000001.SZ'，为空则获取所有股票
        trade_date: 交易日期，格式YYYYMMDD，如'20180726'
        start_date: 开始日期，格式YYYYMMDD
        end_date: 结束日期，格式YYYYMMDD
        fields: 指定字段，如'ts_code,trade_date,turnover_rate,volume_ratio,pe,pb'

    Returns:
        包含日指标数据的字典

    Examples:
        获取指定日期所有股票基本指标: get_daily_basic('', '20180726')
        获取指定股票时间范围数据: get_daily_basic('000001.SZ', '', '20180701', '20180731')
        获取指定字段: get_daily_basic('000001.SZ', '20180726', '', '', 'ts_code,trade_date,turnover_rate,pe,pb')
    """
    try:
        print(f"🔄 开始获取日指标数据 - 股票代码: {ts_code or '全部'}, 交易日期: {trade_date or '范围查询'}")

        # 参数验证：必须提供交易日期或日期范围
        if not trade_date and not (start_date and end_date):
            return {
                "success": False,
                "message": "必须提供trade_date或start_date+end_date参数"
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
        if fields:
            params['fields'] = fields
        else:
            # 默认常用字段
            params['fields'] = 'ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pb,ps,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'

        print(f"📅 查询参数: {params}")
        print(f"🔌 调用Tushare daily_basic接口...")

        df = pro.daily_basic(**params)

        if df is None or df.empty:
            return {
                "success": False,
                "message": "未获取到日指标数据，可能是非交易日或参数错误"
            }

        print(f"✅ 成功获取 {len(df)} 条日指标数据")

        # 数据预处理
        if 'trade_date' in df.columns and 'ts_code' in df.columns:
            df = df.sort_values(['trade_date', 'ts_code'], ascending=[True, True])

        # 保存CSV文件用于调试
        try:
            from pathlib import Path
            from datetime import datetime

            # 获取项目根目录
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent
            csv_dir = project_root / "data" / "debug_csv" / "daily_basic_tool"
            csv_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名（包含daily_basic标识）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = csv_dir / f"daily_basic_{ts_code or 'multi'}_{timestamp}.csv"

            # 保存CSV
            df.to_csv(csv_filename, index=False, encoding='utf-8')
            print(f"📁 日指标数据已保存到: {csv_filename}")

        except Exception as csv_error:
            print(f"⚠️ CSV保存失败: {csv_error}")

        # 统一返回格式
        return {
            "success": True,
            "message": f"成功获取日指标数据，共 {len(df)} 条记录",
            "extracted_data": {
                "ts_code": ts_code or "多股票",
                "data_type": "daily_basic",
                "count": len(df),
                "data": df.to_dict('records')
            }
        }

    except Exception as e:
        error_msg = f"获取日指标数据失败: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg
        }
