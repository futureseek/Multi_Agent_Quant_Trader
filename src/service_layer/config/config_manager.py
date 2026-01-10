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
        
        # 设置prompt配置文件路径
        project_root = Path(__file__).parent.parent.parent.parent
        self.prompt_config_path = project_root / "config" / "prompt_config.json"
        
        self._config_data = None
        self._prompt_config_data = None
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            # 加载API配置
            if not self.config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
            
            print(f"✅ API配置文件加载成功: {self.config_path}")
            
            # 加载Prompt配置（可选）
            self._load_prompt_config()
            
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            raise
    
    def _load_prompt_config(self) -> None:
        """加载Prompt配置文件"""
        try:
            if self.prompt_config_path.exists():
                with open(self.prompt_config_path, 'r', encoding='utf-8') as f:
                    self._prompt_config_data = json.load(f)
                print(f"✅ Prompt配置文件加载成功: {self.prompt_config_path}")
            else:
                print(f"⚠️  Prompt配置文件不存在: {self.prompt_config_path}")
                self._prompt_config_data = {}
        except Exception as e:
            print(f"⚠️  Prompt配置文件加载失败: {e}，将使用默认配置")
            self._prompt_config_data = {}
    
    def get_model_config(self, agent_name: str) -> Dict[str, Any]:
        """
        获取指定Agent的模型配置
        
        Args:
            agent_name: Agent名称 (如: handler_agent, strategy_agent)
            
        Returns:
            模型配置字典，只包含ChatOpenAI支持的参数
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
        
        # 只返回ChatOpenAI支持的参数，过滤掉无效参数
        valid_config = {
            "model_name": agent_config["model_name"],
            "api_key": agent_config["api_key"],
            "base_url": agent_config["base_url"]
        }


        
        return valid_config
    
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
    
    def get_prompt_config(self, agent_name: str) -> str:
        """
        获取指定Agent的系统提示词
        
        Args:
            agent_name: Agent名称 (如: handler_agent, strategy_agent)
            
        Returns:
            系统提示词字符串
        """
        # 如果prompt配置不存在，返回默认提示词
        if not self._prompt_config_data:
            return self._get_default_prompt(agent_name)
        
        # 从配置中获取提示词
        agent_prompt = self._prompt_config_data.get(agent_name)
        
        if agent_prompt:
            return agent_prompt
        else:
            print(f"⚠️  未找到Agent '{agent_name}' 的prompt配置，使用默认配置")
            return self._get_default_prompt(agent_name)
    
    def _get_default_prompt(self, agent_name: str) -> str:
        """获取默认提示词"""
        default_prompts = {
            "handler_agent": "你是一个专业的量化投资AI助手。你的任务是帮助用户进行投资分析、策略制定和风险评估。请以专业、友好的态度回应用户的问题。"
        }
        
        return default_prompts.get(agent_name, "你是一个AI助手，请帮助用户解决问题。")
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取完整配置数据"""
        if not self._config_data:
            raise RuntimeError("配置文件未加载")
        
        return self._config_data.copy()

# 全局配置管理器实例
config_manager = ConfigManager()
