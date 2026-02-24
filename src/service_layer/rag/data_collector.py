"""
数据收集模块 - 基于Tushare

收集股票基础信息和财务数据，用于构建向量知识库
"""

import tushare as ts
import pandas as pd
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import time


class StockDataCollector:
    """股票数据收集器"""

    def __init__(self, tushare_token: str):
        """
        初始化数据收集器

        Args:
            tushare_token: Tushare API Token
        """
        print("🔧 初始化Tushare数据收集器...")
        ts.set_token(tushare_token)
        self.pro = ts.pro_api()
        print("✅ Tushare API连接成功")

    def collect_basic_info(self) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        收集股票基本信息

        Returns:
            (documents, metadatas, ids)
            - documents: 文档内容列表
            - metadatas: 元数据列表
            - ids: 文档ID列表
        """
        print("📊 开始收集股票基本信息...")

        try:
            # 获取股票列表
            stock_list = self.pro.stock_basic(
                exchange='',
                list_status='L',  # 只获取上市股票
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )

            print(f"✅ 获取到 {len(stock_list)} 只股票")

            documents = []
            metadatas = []
            ids = []

            for _, row in stock_list.iterrows():
                # 构建文档内容
                doc = f"""股票代码: {row['ts_code']}
股票名称: {row['name']}
所属区域: {row['area']}
所属行业: {row['industry']}
交易市场: {row['market']}
上市日期: {row['list_date']}"""

                documents.append(doc.strip())
                metadatas.append({
                    'symbol': row['ts_code'],
                    'name': row['name'],
                    'industry': row['industry'],
                    'area': row['area'],
                    'market': row['market'],
                    'list_date': row['list_date']
                })
                ids.append(row['ts_code'])

            print(f"✅ 成功构建 {len(documents)} 个基本信息文档")

            return documents, metadatas, ids

        except Exception as e:
            print(f"❌ 收集基本信息失败: {e}")
            return [], [], []

    def collect_financial_data(
        self,
        symbols: Optional[List[str]] = None,
        trade_date: Optional[str] = None
    ) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        收集财务指标数据

        Args:
            symbols: 股票代码列表，None表示全部
            trade_date: 交易日期（YYYYMMDD格式），None表示最新交易日

        Returns:
            (documents, metadatas, ids)
        """
        print("📊 开始收集财务指标数据...")

        try:
            # 如果没有指定日期，获取最新交易日
            if trade_date is None:
                today = datetime.now().strftime('%Y%m%d')
                cal_df = self.pro.trade_cal(
                    exchange='SSE',
                    start_date='20200101',
                    end_date=today
                )
                # 获取最近的交易日
                trade_dates = cal_df[cal_df['is_open'] == 1]['cal_date'].tolist()
                trade_date = trade_dates[-1] if trade_dates else today

            print(f"📅 查询日期: {trade_date}")

            # 获取每日基本面指标
            df = self.pro.daily_basic(
                ts_code=symbols,
                trade_date=trade_date,
                fields='ts_code,trade_date,pe,pb,ps,dv_ratio,total_mv,circ_mv'
            )

            if df.empty:
                print(f"⚠️ 未找到 {trade_date} 的财务数据")
                return [], [], []

            print(f"✅ 获取到 {len(df)} 只股票的财务数据")

            documents = []
            metadatas = []
            ids = []

            for _, row in df.iterrows():
                # 构建文档内容
                doc = f"""股票代码: {row['ts_code']}
交易日期: {row['trade_date']}
市盈率(PE): {row['pe']}
市净率(PB): {row['pb']}
市销率(PS): {row['ps']}
股息率: {row['dv_ratio']}%
总市值(亿元): {row['total_mv']}
流通市值(亿元): {row['circ_mv']}"""

                documents.append(doc.strip())
                metadatas.append({
                    'symbol': row['ts_code'],
                    'date': row['trade_date'],
                    'pe': float(row['pe']) if pd.notna(row['pe']) else 0.0,
                    'pb': float(row['pb']) if pd.notna(row['pb']) else 0.0,
                    'total_mv': float(row['total_mv']) if pd.notna(row['total_mv']) else 0.0,
                    'circ_mv': float(row['circ_mv']) if pd.notna(row['circ_mv']) else 0.0
                })
                ids.append(f"{row['ts_code']}_{row['trade_date']}")

            print(f"✅ 成功构建 {len(documents)} 个财务数据文档")

            return documents, metadatas, ids

        except Exception as e:
            print(f"❌ 收集财务数据失败: {e}")
            return [], [], []

    def collect_and_build_knowledge_base(
        self,
        vector_store,
        collect_basic: bool = True,
        collect_financial: bool = True
    ) -> Dict[str, Any]:
        """
        一站式收集数据并构建向量库

        Args:
            vector_store: StockVectorStore实例
            collect_basic: 是否收集基本信息
            collect_financial: 是否收集财务数据

        Returns:
            操作结果汇总
        """
        results = {
            "success": True,
            "basic_info": None,
            "financial": None
        }

        # 1. 收集并添加基本信息
        if collect_basic:
            print("\n" + "="*50)
            print("📌 开始处理基本信息...")
            print("="*50)

            docs, metadatas, ids = self.collect_basic_info()

            if docs:
                result = vector_store.add_documents(
                    collection_name='stock_basic_info',
                    documents=docs,
                    metadatas=metadatas,
                    ids=ids
                )
                results["basic_info"] = result

                if not result["success"]:
                    results["success"] = False

            # 短暂延迟，避免API限流
            time.sleep(0.5)

        # 2. 收集并添加财务数据
        if collect_financial:
            print("\n" + "="*50)
            print("📌 开始处理财务数据...")
            print("="*50)

            docs, metadatas, ids = self.collect_financial_data()

            if docs:
                result = vector_store.add_documents(
                    collection_name='stock_financial',
                    documents=docs,
                    metadatas=metadatas,
                    ids=ids
                )
                results["financial"] = result

                if not result["success"]:
                    results["success"] = False

        return results

    def get_trade_date_list(
        self,
        start_date: str,
        end_date: str,
        exchange: str = 'SSE'
    ) -> List[str]:
        """
        获取交易日列表

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            exchange: 交易所 (SSE=上交所, SZSE=深交所)

        Returns:
            交易日期列表
        """
        try:
            df = self.pro.trade_cal(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )

            # 过滤出交易日
            trade_dates = df[df['is_open'] == 1]['cal_date'].tolist()

            return trade_dates

        except Exception as e:
            print(f"❌ 获取交易日列表失败: {e}")
            return []
