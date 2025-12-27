"""
配置管理模块
负责读取和验证API配置信息
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "api_config.json"
        
        self.config_path = Path(config_path)
        self._config_data = None
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
            
            print(f"✅ 配置文件加载成功: {self.config_path}")
            
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            raise
    
    def get_model_config(self, agent_name: str) -> Dict[str, Any]:
        """
        获取指定Agent的模型配置
        
        Args:
            agent_name: Agent名称 (如: handler_agent, strategy_agent)
            
        Returns:
            模型配置字典
        """
        if not self._config_data:
            raise RuntimeError("配置文件未加载")
        
        model_configs = self._config_data.get("model", {})
        agent_config = model_configs.get(agent_name)
        
        if not agent_config:
            raise KeyError(f"未找到Agent '{agent_name}' 的配置")
        
        # 验证必要字段
        required_fields = ["model_name", "api_key", "base_url"]
        for field in required_fields:
            if field not in agent_config:
                raise ValueError(f"Agent '{agent_name}' 缺少必要配置字段: {field}")
        
        return agent_config
    
    def get_tushare_config(self) -> str:
        """获取Tushare API配置"""
        if not self._config_data:
            raise RuntimeError("配置文件未加载")
        
        return self._config_data.get("tushare_api", "")
    
    def validate_config(self) -> bool:
        """验证配置文件的完整性"""
        try:
            if not self._config_data:
                return False
            
            # 检查基本结构
            if "model" not in self._config_data:
                print("❌ 配置文件缺少 'model' 字段")
                return False
            
            # 检查每个Agent的配置
            model_configs = self._config_data["model"]
            for agent_name, config in model_configs.items():
                try:
                    self.get_model_config(agent_name)
                    print(f"✅ Agent '{agent_name}' 配置验证通过")
                except Exception as e:
                    print(f"❌ Agent '{agent_name}' 配置验证失败: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ 配置验证过程中出错: {e}")
            return False
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取完整配置数据"""
        if not self._config_data:
            raise RuntimeError("配置文件未加载")
        
        return self._config_data.copy()

# 全局配置管理器实例
config_manager = ConfigManager()
