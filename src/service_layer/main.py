"""
Service层主入口文件
初始化和启动Service层服务
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.service_layer.config.config_manager import config_manager
from src.service_layer.api.service import service_api, sync_test_system

def main():
    """Service层主函数"""
    print("🚀 启动Service层服务...")
    
    try:
        # 验证配置
        print("\n📋 验证配置文件...")
        if not config_manager.validate_config():
            print("❌ 配置文件验证失败")
            return False
        
        # 初始化Service API
        print("\n🔧 初始化Service API...")
        # service_api已经在导入时初始化
        
        # 系统自测试
        print("\n🧪 执行系统自测试...")
        test_result = sync_test_system()
        
        if test_result["success"]:
            print("✅ Service层启动成功！")
            print(f"🎯 系统状态: {test_result['system_status']}")
            return True
        else:
            print(f"❌ Service层启动失败: {test_result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ Service层启动异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
