"""
东方财富新闻爬虫

爬取东方财富网股票新闻标题、时间、链接等信息
支持自动向量化存储到ChromaDB
"""

import requests
from datetime import datetime
import json
import time
import re
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.service_layer.rag.vector_store import StockVectorStore
    VECTORIZE_AVAILABLE = True
except ImportError:
    VECTORIZE_AVAILABLE = False
    print("⚠️ 向量化模块不可用，将仅保存JSON文件")


def load_company_map():
    """加载公司名到股票代码的映射表"""
    try:
        map_file = os.path.join(os.path.dirname(__file__), '../data/company_stock_map.json')
        if os.path.exists(map_file):
            with open(map_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# 全局加载映射表
COMPANY_STOCK_MAP = load_company_map()


def extract_stock_from_title(title):
    """
    从标题中提取股票代码

    Args:
        title: 新闻标题

    Returns:
        list: 股票代码列表，格式如 ['600909.SH']
    """
    stocks = []

    # 方法1: 直接从标题提取6位数字代码
    codes = re.findall(r'\d{6}', title)
    for code in codes:
        if code.startswith('6'):
            stocks.append(f"{code}.SH")
        elif code.startswith(('0', '3')):
            stocks.append(f"{code}.SZ")

    # 方法2: 从公司名映射表查找
    if not stocks and COMPANY_STOCK_MAP:
        # 标题格式通常是 "公司名:公告内容"
        # 提取公司名（冒号前的部分）
        if ':' in title:
            company_name = title.split(':')[0].strip()

            # 去掉可能的特殊标记（如 *ST、ST、-U等）
            clean_name = company_name
            # 移除ST标记
            if clean_name.startswith('*ST'):
                clean_name = clean_name[3:]
            elif clean_name.startswith('ST'):
                clean_name = clean_name[2:]
            # 移除科创板标记（-U、-V等）
            if '-U' in clean_name:
                clean_name = clean_name.replace('-U', '')
            if '-V' in clean_name:
                clean_name = clean_name.replace('-V', '')

            # 查找匹配的股票代码（尝试多种变体）
            found = False

            # 1. 精确匹配原始名称
            if company_name in COMPANY_STOCK_MAP:
                stocks.append(COMPANY_STOCK_MAP[company_name])
                found = True

            # 2. 匹配清理后的名称
            elif clean_name in COMPANY_STOCK_MAP:
                stocks.append(COMPANY_STOCK_MAP[clean_name])
                found = True

            # 3. 模糊匹配（映射表中的名称是标题的一部分，或反之）
            if not found:
                for name, code in COMPANY_STOCK_MAP.items():
                    # 清理映射表中的名称（去除后缀）
                    map_clean = name.replace('-U', '').replace('-V', '')
                    # 双向模糊匹配
                    if name in title or map_clean in title or company_name in name or clean_name in name:
                        stocks.append(code)
                        found = True
                        break  # 只取第一个匹配的

    return stocks


def crawl_eastmoney_news(limit=500):
    """
    爬取东方财富网新闻快讯（支持分页）

    Args:
        limit: 爬取新闻数量（默认500条）

    Returns:
        list: 新闻列表
    """
    api_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.eastmoney.com/'
    }

    news_list = []
    page_size = 50
    page_index = 1

    while len(news_list) < limit:
        params = {
            'sr': '-1',
            'page_size': page_size,
            'page_index': page_index,
            'ann_type': 'SHA,SHE',
            'client_source': 'web',
            'f_node': '0',
            's_node': '0'
        }

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                break

            data = response.json()
            if 'data' not in data or 'list' not in data['data']:
                break

            announcements = data['data']['list']
            if not announcements:
                break

            for item in announcements:
                title = item.get('title', '')
                related_stocks = extract_stock_from_title(title)

                url = item.get('url', '')
                if not url and related_stocks:
                    code = related_stocks[0].replace('.SH', '').replace('.SZ', '')
                    url = f"https://data.eastmoney.com/notices/{code}.html"
                elif not url:
                    url = 'https://data.eastmoney.com/notices/'

                if title:
                    news_list.append({
                        'title': title,
                        'url': url,
                        'pub_time': item.get('notice_date', ''),
                        'related_stocks': related_stocks,
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'eastmoney_api'
                    })

                if len(news_list) >= limit:
                    break

            print(f"Progress: {len(news_list)}/{limit}")
            page_index += 1
            time.sleep(0.3)

        except Exception:
            break

    return news_list


def vectorize_news(news_list, vector_store):
    """
    将新闻向量化存储到ChromaDB

    Args:
        news_list: 新闻列表
        vector_store: StockVectorStore实例

    Returns:
        success_count: 成功向量化数量
    """
    if not VECTORIZE_AVAILABLE or not vector_store:
        return 0

    try:
        # 准备数据
        documents = []
        metadatas = []
        ids = []

        for i, news in enumerate(news_list):
            # 使用标题作为文档内容
            doc = news['title']

            # 元数据
            metadata = {
                'pub_time': news.get('pub_time', ''),
                'stocks': json.dumps(news.get('related_stocks', []), ensure_ascii=False),
                'url': news.get('url', ''),
                'source': news.get('source', 'eastmoney')
            }

            # 生成唯一ID（使用标题的hash）
            import hashlib
            doc_id = hashlib.md5(doc.encode('utf-8')).hexdigest()

            documents.append(doc)
            metadatas.append(metadata)
            ids.append(doc_id)

        # 批量添加到market_news collection
        result = vector_store.add_documents(
            collection_name='market_news',
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        if result['success']:
            return result['count']
        else:
            print(f"❌ 向量化失败: {result.get('error')}")
            return 0

    except Exception as e:
        print(f"❌ 向量化异常: {e}")
        return 0


def save_news_to_json(news_list, filename='data/news_sample.json'):
    """保存新闻数据到JSON文件（增量模式，自动去重）"""
    # 读取已有数据
    existing = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    # 用标题去重
    existing_titles = {n['title'] for n in existing}
    new_news = [n for n in news_list if n['title'] not in existing_titles]

    if not new_news:
        print(f"No new news (skipped {len(news_list)} duplicates)")
        return 0, len(news_list), []

    # 合并保存
    combined = existing + new_news
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    return len(new_news), len(news_list) - len(new_news), new_news


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='爬取东方财富新闻并支持向量化')
    parser.add_argument('number', nargs='?', type=int, default=500, help='爬取新闻数量')
    parser.add_argument('--no-vectorize', action='store_true', help='跳过向量化')
    parser.add_argument('--vectorize-only', action='store_true', help='仅向量化已有数据')

    args = parser.parse_args()

    # 向量化模式
    vector_store = None
    if not args.no_vectorize and VECTORIZE_AVAILABLE:
        print("Initializing vector store...")
        vector_store = StockVectorStore(persist_dir='./data/chroma_db')

    # 仅向量化模式
    if args.vectorize_only:
        if not vector_store:
            print("❌ 向量化模块不可用")
            sys.exit(1)

        if not os.path.exists('data/news_sample.json'):
            print("❌ 新闻数据文件不存在")
            sys.exit(1)

        with open('data/news_sample.json', 'r', encoding='utf-8') as f:
            existing_news = json.load(f)

        print(f"Vectorizing {len(existing_news)} existing news...")
        count = vectorize_news(existing_news, vector_store)
        print(f"✅ 向量化完成: {count} 条")
        sys.exit(0)

    # 爬取新闻
    print(f"Crawling {args.number} news from EastMoney...")
    news = crawl_eastmoney_news(limit=args.number)

    # 保存JSON
    added, skipped, new_news = save_news_to_json(news)

    # 向量化（只向量化新增的新闻）
    vectorized = 0
    if vector_store and added > 0:
        print(f"\nVectorizing {added} new news...")
        vectorized = vectorize_news(new_news, vector_store)

    # 统计
    with_stocks = sum(1 for n in news if n['related_stocks'])

    with open('data/news_sample.json', 'r', encoding='utf-8') as f:
        total_in_db = len(json.load(f))

    print(f"\nCompleted:")
    print(f"  - Crawled: {len(news)} news")
    print(f"  - Added: {added} new")
    print(f"  - Skipped: {skipped} duplicates")
    print(f"  - Vectorized: {vectorized} news")
    print(f"  - With stock codes: {with_stocks} ({with_stocks/len(news)*100:.1f}%)")
    print(f"  - Total in database: {total_in_db}")
    print(f"Saved to: data/news_sample.json")
