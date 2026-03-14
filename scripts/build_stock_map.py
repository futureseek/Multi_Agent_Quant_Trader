"""
构建公司名称到股票代码的映射表

使用Tushare API获取所有A股基本信息，建立公司名->代码映射
"""

import tushare as ts
import json
import os


def build_company_stock_map():
    """
    获取所有A股股票基本信息，构建公司名->代码映射
    """
    print("🔍 正在从Tushare获取股票列表...")

    # 读取配置
    config_path = os.path.join(os.path.dirname(__file__), '../config/api_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    api_token = config.get('tushare_api')
    if not api_token:
        print("❌ 未找到Tushare API Token")
        return {}

    # 初始化Tushare
    ts.set_token(api_token)
    pro = ts.pro_api()

    company_map = {}

    try:
        # 获取股票基本信息
        print("📡 获取股票基本信息...")
        df = pro.stock_basic(exchange='', list_status='L',
                             fields='ts_code,name,area,industry,list_date')

        print(f"✅ 获取到 {len(df)} 只股票")

        # 构建映射表
        for _, row in df.iterrows():
            ts_code = row['ts_code']  # 如 600000.SH
            name = row['name']         # 公司名称

            # 简称映射
            company_map[name] = ts_code

            # 处理名称中的特殊字符（如ST、*ST等）
            # 同时保存带前缀和不带前缀的版本
            if name.startswith('*ST'):
                clean_name = name[3:]  # 去掉*ST
                company_map[clean_name] = ts_code
            elif name.startswith('ST'):
                clean_name = name[2:]  # 去掉ST
                company_map[clean_name] = ts_code

        print(f"\n✅ 映射表构建完成！")
        print(f"📊 总计: {len(company_map)} 个公司名称映射")

        # 显示示例
        print(f"\n📝 映射示例:")
        for i, (name, code) in enumerate(list(company_map.items())[:10]):
            print(f"   {name} -> {code}")

        return company_map

    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return {}


def save_map_to_json(company_map, filename='data/company_stock_map.json'):
    """保存映射表到JSON文件"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(company_map, f, ensure_ascii=False, indent=2)
        print(f"\n💾 映射表已保存到: {filename}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")


def load_company_map(filename='data/company_stock_map.json'):
    """从JSON文件加载映射表"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ 加载映射表失败: {e}")
    return {}


if __name__ == "__main__":
    print("=" * 60)
    print("构建公司名称->股票代码映射表")
    print("=" * 60)
    print()

    # 构建映射表
    company_map = build_company_stock_map()

    if company_map:
        # 保存到JSON
        save_map_to_json(company_map)

        print("\n" + "=" * 60)
        print("✅ 完成！")
        print("=" * 60)
    else:
        print("\n❌ 构建失败")
