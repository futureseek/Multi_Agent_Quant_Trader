#!/usr/bin/env python3
"""
测试新增的两个Tushare工具
独立测试脚本，直接测试工具函数，不依赖Agent
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append('/home/ligenghao/Multi_Agent_Quant_Trader')


def test_adj_factor_tool():
    """测试复权因子工具"""
    print("🧪 测试 1: 复权因子工具")
    print("=" * 50)
    
    try:
        from src.service_layer.tools.adj_factor_tool import get_adj_factor
        
        # 测试用例1: 获取指定日期所有股票复权因子
        print("📊 测试用例1: 指定日期所有股票复权因子")
        result1 = get_adj_factor.invoke({
            "ts_code": "",
            "trade_date": '20241210'
        })
        print(f"结果长度: {len(result1)}")
        print(f"前200字符: {result1[:200]}...")
        
        # 测试用例2: 获取平安银行全部复权因子
        print("\n📊 测试用例2: 平安银行历史复权因子")
        result2 = get_adj_factor.invoke({
            "ts_code": '000001.SZ',
            "trade_date": '',
            "start_date": '20241201',
            "end_date": '20241210'
        })
        print(f"结果长度: {len(result2)}")
        print(f"前200字符: {result2[:200]}...")
        
        # 测试用例3: 获取指定股票指定日期复权因子
        print("\n📊 测试用例3: 指定股票指定日期")
        result3 = get_adj_factor.invoke({
            "ts_code": '000002.SZ',
            "trade_date": '20241210'
        })
        print(f"结果长度: {len(result3)}")
        print(f"前200字符: {result3[:200]}...")
        
        print("✅ 复权因子工具测试完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 复权因子工具测试失败: {e}")
        return False

def test_daily_basic_tool():
    """测试日指标工具"""
    print("🧪 测试 2: 日指标工具")
    print("=" * 50)
    
    try:
        from src.service_layer.tools.daily_basic_tool import get_daily_basic
        
        # 测试用例1: 获取指定日期所有股票基本指标
        print("📊 测试用例1: 指定日期市场概览")
        result1 = get_daily_basic.invoke({
            "ts_code": '',
            "trade_date": '20241210'
        })
        print(f"结果长度: {len(result1)}")
        print(f"前200字符: {result1[:200]}...")
        
        # 测试用例2: 获取平安银行时间范围数据
        print("\n📊 测试用例2: 平安银行基本面指标")
        result2 = get_daily_basic.invoke({
            "ts_code": '000001.SZ',
            "start_date": '20241201',
            "end_date": '20241210'
        })
        print(f"结果长度: {len(result2)}")
        print(f"前200字符: {result2[:200]}...")
        
        # 测试用例3: 获取指定字段
        print("\n📊 测试用例3: 自定义字段")
        result3 = get_daily_basic.invoke({
            "ts_code": '000002.SZ',
            "trade_date": '20241210',
            "fields": 'ts_code,trade_date,close,pe,pb,turnover_rate,total_mv'
        })
        print(f"结果长度: {len(result3)}")
        print(f"前200字符: {result3[:200]}...")
        
        print("✅ 日指标工具测试完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 日指标工具测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    print("🧪 测试 3: 错误处理")
    print("=" * 50)
    
    try:
        from src.service_layer.tools.adj_factor_tool import get_adj_factor
        from src.service_layer.tools.daily_basic_tool import get_daily_basic
        
        # 测试错误的股票代码
        print("📊 测试错误股票代码")
        result1 = get_adj_factor.invoke({
            "ts_code": 'INVALID_CODE',
            "trade_date": '20241210'
        })
        print(f"错误处理结果: {result1[:100]}...")
        
        # 测试缺少必要参数
        print("\n📊 测试缺少必要参数")
        result2 = get_daily_basic.invoke({})
        print(f"错误处理结果: {result2[:100]}...")
        
        # 测试复权因子缺少参数
        print("\n📊 测试复权因子缺少参数")
        result3 = get_adj_factor.invoke({
            "ts_code": "",
            "trade_date": ""
        })
        print(f"错误处理结果: {result3[:100]}...")
        
        print("✅ 错误处理测试完成\n")
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试新增的Tushare工具")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    
    test_results = []
    
    # 执行所有测试
    test_results.append(("复权因子工具", test_adj_factor_tool()))
    test_results.append(("日指标工具", test_daily_basic_tool()))
    test_results.append(("错误处理", test_error_handling()))
    
    # 汇总结果
    print("🏁 测试结果汇总")
    print("=" * 80)
    
    success_count = 0
    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:20} : {status}")
        if success:
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(test_results)} 测试通过")
    
    if success_count == len(test_results):
        print("🎉 所有工具测试通过！可以安全使用这些工具。")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接。")
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试过程出现异常: {e}")
        exit(1)
