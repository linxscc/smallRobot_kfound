"""
YAML配置管理模块

功能：从YAML配置文件读取任务参数、系统配置等
支持的配置项：
  - 任务定义（多个目标点、超时、优先级）
  - 导航参数（速度参考、路径计划算法等）
  - 系统参数（日志级别、重试策略等）
"""

import yaml
import os
from typing import Dict, List, Optional
from dataclasses import asdict

from .logger_module import get_logger


class ConfigManager:
    """YAML配置管理器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.logger = get_logger("ConfigManager")
        
        # 默认配置目录
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__),
                '..',
                'config'
            )
        
        self.config_dir = config_dir
        self.configs: Dict = {}
        
        # 确保目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        self.logger.info(f"配置管理器初始化，配置目录: {config_dir}")
    
    def load_config(self, config_name: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_name: 配置文件名（不含.yaml后缀）
            
        Returns:
            配置字典
        """
        config_path = os.path.join(self.config_dir, f"{config_name}.yaml")
        
        if not os.path.exists(config_path):
            self.logger.warn(f"配置文件不存在: {config_path}")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            self.configs[config_name] = config
            self.logger.info(f"配置 {config_name} 已加载")
            return config
        
        except Exception as e:
            self.logger.error(f"读取配置文件失败: {str(e)}")
            return {}
    
    def save_config(self, config_name: str, config_data: Dict) -> bool:
        """
        保存配置到文件
        
        Args:
            config_name: 配置文件名
            config_data: 配置数据
            
        Returns:
            是否保存成功
        """
        config_path = os.path.join(self.config_dir, f"{config_name}.yaml")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            self.configs[config_name] = config_data
            self.logger.info(f"配置 {config_name} 已保存到 {config_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def get_tasks(self, config_name: str = 'tasks') -> List[Dict]:
        """获取任务配置列表"""
        config = self.load_config(config_name)
        return config.get('tasks', [])
    
    def get_task_by_name(self, task_name: str, config_name: str = 'tasks') -> Optional[Dict]:
        """按名称获取任务配置"""
        tasks = self.get_tasks(config_name)
        for task in tasks:
            if task.get('name') == task_name:
                return task
        return None
    
    def get_navigation_params(self, config_name: str = 'navigation') -> Dict:
        """获取导航参数"""
        config = self.load_config(config_name)
        return config.get('parameters', {})
    
    def get_system_params(self, config_name: str = 'system') -> Dict:
        """获取系统参数"""
        config = self.load_config(config_name)
        return config.get('parameters', {})


def create_default_configs(config_dir: str):
    """创建默认配置文件"""
    os.makedirs(config_dir, exist_ok=True)
    
    # 任务配置示例
    tasks_config = {
        'description': '多点位任务配置示例',
        'tasks': [
            {
                'name': 'demo_task_1',
                'description': '演示任务1：2个点位',
                'waypoints': [
                    {
                        'order': 1,
                        'x': 5.0,
                        'y': 5.0,
                        'theta': 0.0,
                        'name': '充电站',
                        'timeout': 20.0
                    },
                    {
                        'order': 2,
                        'x': 10.0,
                        'y': 10.0,
                        'theta': 0.0,
                        'name': '检查点A',
                        'timeout': 20.0
                    }
                ]
            },
            {
                'name': 'demo_task_2',
                'description': '演示任务2：巡检路线',
                'waypoints': [
                    {
                        'order': 1,
                        'x': 0.0,
                        'y': 0.0,
                        'theta': 0.0,
                        'name': '起点',
                        'timeout': 15.0
                    },
                    {
                        'order': 2,
                        'x': 10.0,
                        'y': 0.0,
                        'theta': 0.0,
                        'name': '检查点1',
                        'timeout': 20.0
                    },
                    {
                        'order': 3,
                        'x': 10.0,
                        'y': 10.0,
                        'theta': 0.0,
                        'name': '检查点2',
                        'timeout': 20.0
                    },
                    {
                        'order': 4,
                        'x': 0.0,
                        'y': 10.0,
                        'theta': 0.0,
                        'name': '检查点3',
                        'timeout': 20.0
                    }
                ]
            }
        ]
    }
    
    # 导航参数配置
    navigation_config = {
        'description': '导航系统参数',
        'parameters': {
            'max_velocity': 1.0,                    # 最大速度 (m/s)
            'max_angular_velocity': 1.0,            # 最大角速度 (rad/s)
            'acceleration_limit': 0.5,              # 加速度限制
            'costmap_size': 10.0,                   # 代价地图大小
            'planning_algorithm': 'A*',             # 路径规划算法
            'replanning_period': 1.0                # 重新规划周期
        }
    }
    
    # 系统参数配置
    system_config = {
        'description': '系统运行参数',
        'parameters': {
            'simulation_mode': True,                # 是否使用模拟模式
            'log_level': 'INFO',                    # 日志级别
            'enable_rosbag_recording': True,        # 是否记录rosbag
            'rosbag_path': '/tmp/robot_rosbag',     # rosbag保存路径
            'task_timeout_default': 30.0,           # 默认任务超时时间
            'retry_on_failure': False,              # 失败是否重试
            'max_retries': 3                        # 最大重试次数
        }
    }
    
    # 保存默认配置
    config_manager = ConfigManager(config_dir)
    config_manager.save_config('tasks', tasks_config)
    config_manager.save_config('navigation', navigation_config)
    config_manager.save_config('system', system_config)
    
    return config_manager
