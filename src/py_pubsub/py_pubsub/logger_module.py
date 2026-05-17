"""
日志模块

功能：统一管理系统的日志输出
设计理由：
  - 集中式日志管理便于调试和问题追踪
  - 支持不同级别的日志输出（DEBUG, INFO, WARN, ERROR）
  - 时间戳确保事件的因果关系清晰
  - 便于后续添加文件和远程日志功能
"""

from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class TaskLogger:
    """
    任务日志记录器
    
    提供统一的日志接口，所有系统组件都通过此类记录日志。
    """
    
    def __init__(self, task_id: Optional[str] = None):
        """
        初始化日志记录器
        
        Args:
            task_id: 任务ID，用于关联日志
        """
        self.task_id = task_id or "SYSTEM"
        self.logs = []  # 保存所有日志记录
    
    def _format_message(self, level: LogLevel, message: str) -> str:
        """
        格式化日志消息
        
        格式: [TIME] [TASK_ID] [LEVEL] MESSAGE
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return f"[{timestamp}] [{self.task_id}] [{level.value}] {message}"
    
    def debug(self, message: str):
        """记录调试信息"""
        formatted = self._format_message(LogLevel.DEBUG, message)
        print(formatted)
        self.logs.append((LogLevel.DEBUG, formatted))
    
    def info(self, message: str):
        """记录普通信息"""
        formatted = self._format_message(LogLevel.INFO, message)
        print(formatted)
        self.logs.append((LogLevel.INFO, formatted))
    
    def warn(self, message: str):
        """记录警告信息"""
        formatted = self._format_message(LogLevel.WARN, message)
        print(f"\033[93m{formatted}\033[0m")  # 黄色输出
        self.logs.append((LogLevel.WARN, formatted))
    
    def error(self, message: str):
        """记录错误信息"""
        formatted = self._format_message(LogLevel.ERROR, message)
        print(f"\033[91m{formatted}\033[0m")  # 红色输出
        self.logs.append((LogLevel.ERROR, formatted))
    
    def get_logs(self) -> list:
        """获取所有日志记录"""
        return self.logs.copy()


# 全局日志实例（单例模式）
_global_logger: Optional[TaskLogger] = None


def get_logger(task_id: Optional[str] = None) -> TaskLogger:
    """
    获取全局日志实例
    
    如果是第一次调用，会创建实例。
    后续调用可选择性地更新task_id。
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = TaskLogger(task_id or "SYSTEM")
    elif task_id:
        _global_logger.task_id = task_id
    return _global_logger
