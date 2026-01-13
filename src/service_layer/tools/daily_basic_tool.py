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
) -> str:
    """
    获取股票每日重要基本面指标
    
    Args:
        ts_code: 股票代码，如'000001.SZ'，为空则获取所有股票
        trade_date: 交易日期，格式YYYYMMDD，如'20180726'
        start_date: 开始日期，格式YYYYMMDD
        end_date: 结束日期，格式YYYYMMDD  
        fields: 指定字段，如'ts_code,trade_date,turnover_rate,volume_ratio,pe,pb'
        
    Returns:
        包含日指标数据的JSON字符串
        
    Examples:
        获取指定日期所有股票基本指标: get_daily_basic('', '20180726')
        获取指定股票时间范围数据: get_daily_basic('000001.SZ', '', '20180701', '20180731')
        获取指定字段: get_daily_basic('000001.SZ', '20180726', '', '', 'ts_code,trade_date,turnover_rate,pe,pb')
    """
    try:
        print(f"🔄 开始获取日指标数据 - 股票代码: {ts_code or '全部'}, 交易日期: {trade_date or '范围查询'}")
        
        # 参数验证：必须提供交易日期或日期范围
        if not trade_date and not (start_date and end_date):
            return f"❌ 错误: 必须提供trade_date或start_date+end_date参数"
        
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
        if fields:
            params['fields'] = fields
        else:
            # 默认常用字段
            params['fields'] = 'ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pb,ps,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv'
            
        print(f"📅 查询参数: {params}")
        print(f"🔌 调用Tushare daily_basic接口...")
        
        df = pro.daily_basic(**params)
        
        if df is None or df.empty:
            return f"⚠️ 警告: 未获取到日指标数据，可能是非交易日或参数错误"
        
        print(f"✅ 成功获取 {len(df)} 条日指标数据")
        
        # 数据预处理
        if 'trade_date' in df.columns and 'ts_code' in df.columns:
            df = df.sort_values(['trade_date', 'ts_code'], ascending=[True, True])
        
        # 数值列处理
        numeric_cols = ['close', 'turnover_rate', 'volume_ratio', 'pe', 'pb', 'ps', 
                       'dv_ratio', 'dv_ttm', 'total_share', 'float_share', 'free_share', 
                       'total_mv', 'circ_mv']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 统计分析
        stats = {
            "数据条数": len(df),
            "涉及股票数": df['ts_code'].nunique() if 'ts_code' in df.columns else 0,
            "日期范围": {
                "开始日期": df['trade_date'].min() if 'trade_date' in df.columns else None,
                "结束日期": df['trade_date'].max() if 'trade_date' in df.columns else None
            } if 'trade_date' in df.columns else None,
        }
        
        # 添加关键指标统计
        key_metrics_stats = {}
        for metric in ['pe', 'pb', 'turnover_rate', 'total_mv']:
            if metric in df.columns:
                metric_data = df[metric].dropna()
                if len(metric_data) > 0:
                    key_metrics_stats[metric] = {
                        "平均值": float(metric_data.mean()),
                        "中位数": float(metric_data.median()),
                        "最小值": float(metric_data.min()),
                        "最大值": float(metric_data.max()),
                        "标准差": float(metric_data.std())
                    }
        
        if key_metrics_stats:
            stats["关键指标统计"] = key_metrics_stats
        
        # 格式化结果
        result = {
            "query_params": {
                "ts_code": ts_code or "全部股票",
                "trade_date": trade_date or f"{start_date}至{end_date}",
                "fields": fields or "默认字段"
            },
            "statistics": stats,
            "columns": df.columns.tolist(),
            "sample_data": df.head(10).to_dict('records'),
        }
        
        # 如果是单个股票查询，提供更详细的分析
        if ts_code:
            stock_df = df[df['ts_code'] == ts_code] if 'ts_code' in df.columns else df
            if len(stock_df) > 0:
                latest_data = stock_df.iloc[-1]
                result["stock_analysis"] = {
                    "stock_code": ts_code,
                    "data_count": len(stock_df),
                    "latest_metrics": {
                        "交易日期": latest_data.get('trade_date', 'N/A'),
                        "收盘价": float(latest_data.get('close', 0)) if pd.notna(latest_data.get('close')) else None,
                        "市盈率PE": float(latest_data.get('pe', 0)) if pd.notna(latest_data.get('pe')) else None,
                        "市净率PB": float(latest_data.get('pb', 0)) if pd.notna(latest_data.get('pb')) else None,
                        "换手率": float(latest_data.get('turnover_rate', 0)) if pd.notna(latest_data.get('turnover_rate')) else None,
                        "总市值": float(latest_data.get('total_mv', 0)) if pd.notna(latest_data.get('total_mv')) else None
                    },
                    "recent_data": stock_df.tail(5).to_dict('records') if len(stock_df) > 0 else []
                }
        
        # 如果是单个日期查询，提供市场概览
        if trade_date:
            # PE排序分析
            if 'pe' in df.columns:
                pe_data = df[df['pe'].notna() & (df['pe'] > 0)]
                if len(pe_data) > 0:
                    pe_sorted = pe_data.sort_values('pe')
                    result["market_overview"] = {
                        "trade_date": trade_date,
                        "total_stocks": len(df),
                        "valid_pe_stocks": len(pe_data),
                        "pe_analysis": {
                            "最低PE股票": pe_sorted.head(5)[['ts_code', 'pe', 'pb', 'total_mv']].to_dict('records'),
                            "最高PE股票": pe_sorted.tail(5)[['ts_code', 'pe', 'pb', 'total_mv']].to_dict('records')
                        }
                    }
                    
            # 市值分析
            if 'total_mv' in df.columns:
                mv_data = df[df['total_mv'].notna()]
                if len(mv_data) > 0:
                    mv_sorted = mv_data.sort_values('total_mv', ascending=False)
                    if "market_overview" not in result:
                        result["market_overview"] = {"trade_date": trade_date}
                    result["market_overview"]["market_cap_analysis"] = {
                        "最大市值股票": mv_sorted.head(5)[['ts_code', 'total_mv', 'pe', 'pb']].to_dict('records'),
                        "最小市值股票": mv_sorted.tail(5)[['ts_code', 'total_mv', 'pe', 'pb']].to_dict('records')
                    }
        
        print(f"📊 日指标数据汇总完成")
        
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"获取日指标数据失败: {str(e)}"
        print(f"❌ {error_msg}")
        return f"❌ 错误: {error_msg}"
