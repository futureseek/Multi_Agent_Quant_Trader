#!/usr/bin/env python3
"""
环境变量和LangChain版本调试脚本
"""
import os
import sys

print("=== 环境变量检查 ===")
proxy_vars = []
for key, value in os.environ.items():
    if 'proxy' in key.lower():
        proxy_vars.append(f"{key}: {value}")
        
if proxy_vars:
    print("发现代理相关环境变量:")
    for var in proxy_vars:
        print(f"  {var}")
else:
    print("未发现代理相关环境变量")

print("\n=== LangChain版本信息 ===")
try:
    import langchain
    print(f"langchain版本: {langchain.__version__}")
except:
    print("langchain未安装或导入失败")

try:
    import langchain_openai
    print(f"langchain_openai版本: {langchain_openai.__version__}")
except:
    print("langchain_openai未安装或导入失败")
    
try:
    import langchain_core
    print(f"langchain_core版本: {langchain_core.__version__}")
except:
    print("langchain_core未安装或导入失败")

print("\n=== ChatOpenAI初始化参数测试 ===")
try:
    from langchain_openai import ChatOpenAI
    import inspect
    
    # 获取ChatOpenAI构造函数的签名
    sig = inspect.signature(ChatOpenAI.__init__)
    print("ChatOpenAI.__init__ 支持的参数:")
    for name, param in sig.parameters.items():
        if name != 'self':
            print(f"  {name}: {param}")
            
    print("\n=== 测试最小参数集 ===")
    # 测试最基本的参数
    minimal_config = {
        "model": "claude-4.0-sonnet",  # 注意这里用model而不是model_name
        "api_key": "sk-test",
        "base_url": "https://api.qnaigc.com/v1"
    }
    
    print("测试配置:", minimal_config)
    test_llm = ChatOpenAI(**minimal_config)
    print("✅ 最小参数集创建成功!")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    print(f"错误类型: {type(e)}")
    import traceback
    traceback.print_exc()
