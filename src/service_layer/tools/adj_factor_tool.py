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
) -> str:
    """
    获取股票复权因子数据
    
    Args:
        ts_code: 股票代码，如'000001.SZ'，为空则获取所有股票
        trade_date: 交易日期，格式YYYYMMDD，如'20180718'，为空则获取指定时间范围
        start_date: 开始日期，格式YYYYMMDD，如'20180101'
        end_date: 结束日期，格式YYYYMMDD，如'20181011'
        
    Returns:
        包含复权因子数据的JSON字符串
        
    Examples:
        获取2018年7月18日复权因子: get_adj_factor('', '20180718')
        获取000001全部复权因子: get_adj_factor('000001.SZ', '')
        获取指定时间范围: get_adj_factor('000001.SZ', '', '20180101', '20181231')
    """
    try:
        print(f"🔄 开始获取复权因子 - 股票代码: {ts_code or '全部'}, 交易日期: {trade_date or '范围查询'}")
        
        # 验证参数逻辑
        if not ts_code and not trade_date and not (start_date and end_date):
            return f"❌ 错误: 参数不完整，需要提供以下组合之一:\n1. trade_date(获取指定日期所有股票)\n2. ts_code + trade_date(获取指定股票指定日期)\n3. ts_code + start_date + end_date(获取指定股票时间范围)"
        
        # 验证股票代码格式(如果提供)
        if ts_code and (len(ts_code) != 9 or '.' not in ts_code):
            return f"❌ 错误: 股票代码格式不正确，应为'000001.SZ'格式，当前输入: {ts_code}"
        
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
            return f"⚠️ 警告: 未获取到复权因子数据，请检查参数是否正确"
        
        print(f"✅ 成功获取 {len(df)} 条复权因子数据")
        
        # 数据预处理
        df = df.sort_values(['ts_code', 'trade_date'], ascending=[True, True])
        
        # 统计分析
        stats = {
            "数据条数": len(df),
            "涉及股票数": df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            "日期范围": {
                "开始日期": df['trade_date'].min() if 'trade_date' in df.columns else None,
                "结束日期": df['trade_date'].max() if 'trade_date' in df.columns else None
            } if 'trade_date' in df.columns else None,
            "复权因子范围": {
                "最小值": float(df['adj_factor'].min()) if 'adj_factor' in df.columns else None,
                "最大值": float(df['adj_factor'].max()) if 'adj_factor' in df.columns else None,
                "平均值": float(df['adj_factor'].mean()) if 'adj_factor' in df.columns else None
            } if 'adj_factor' in df.columns else None
        }
        
        # 格式化结果
        result = {
            "query_params": {
                "ts_code": ts_code or "全部股票",
                "trade_date": trade_date or "时间范围查询",
                "start_date": start_date,
                "end_date": end_date
            },
            "statistics": stats,
            "columns": df.columns.tolist(),
            "sample_data": df.head(10).to_dict('records'),  # 显示前10条数据作为样本
        }
        
        # 如果是单个股票查询，提供更详细的信息
        if ts_code:
            stock_df = df[df['ts_code'] == ts_code] if 'ts_code' in df.columns else df
            result["stock_specific"] = {
                "stock_code": ts_code,
                "data_count": len(stock_df),
                "latest_factor": float(stock_df.iloc[-1]['adj_factor']) if len(stock_df) > 0 and 'adj_factor' in stock_df.columns else None,
                "recent_data": stock_df.tail(5).to_dict('records') if len(stock_df) > 0 else []
            }
        
        # 如果是单个日期查询，按复权因子排序显示异常值
        if trade_date:
            if 'adj_factor' in df.columns:
                # 找出复权因子异常的股票
                sorted_df = df.sort_values('adj_factor', ascending=False)
                result["date_specific"] = {
                    "trade_date": trade_date,
                    "stock_count": len(df),
                    "top_adj_factors": sorted_df.head(5).to_dict('records'),  # 复权因子最大的5只
                    "bottom_adj_factors": sorted_df.tail(5).to_dict('records')  # 复权因子最小的5只
                }
        
        print(f"📊 复权因子数据汇总完成")
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"获取复权因子失败: {str(e)}"
        print(f"❌ {error_msg}")
        return f"❌ 错误: {error_msg}"
