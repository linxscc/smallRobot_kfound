"""
任务状态机模块

功能：定义和管理任务的生命周期状态
设计理由：
  - 使用枚举(Enum)确保状态类型安全
  - 状态转移图清晰，易于维护和扩展
  - 提供状态验证方法，防止非法状态转移
"""

from enum import Enum
from typing import Optional, Dict, List


class TaskState(Enum):
    """任务的5种核心状态"""
    
    IDLE = "Idle"           # 初始状态：待任务
    PENDING = "Pending"     # 任务已接收，待执行
    RUNNING = "Running"     # 正在导航执行中
    ARRIVED = "Arrived"     # 成功到达目标
    FAILED = "Failed"       # 执行失败
    
    def __str__(self):
        return self.value


class TaskStateMachine:
    """
    任务状态机
    
    管理任务从创建到完成的整个生命周期。
    使用状态转移表确保转移的合法性。
    """
    
    # 定义合法的状态转移
    VALID_TRANSITIONS: Dict[TaskState, List[TaskState]] = {
        TaskState.IDLE:     [TaskState.PENDING],              # Idle只能→Pending
        TaskState.PENDING:  [TaskState.RUNNING, TaskState.FAILED],  # Pending→Running或Failed
        TaskState.RUNNING:  [TaskState.ARRIVED, TaskState.FAILED],  # Running→Arrived或Failed
        TaskState.ARRIVED:  [TaskState.IDLE],                 # Arrived→Idle（准备下一任务）
        TaskState.FAILED:   [TaskState.IDLE, TaskState.PENDING],    # Failed→Idle或重试
    }
    
    def __init__(self):
        """初始化状态机，起始状态为Idle"""
        self._current_state = TaskState.IDLE
        self._state_history: List[tuple] = []  # (timestamp, state)记录状态变化历史
        self._record_state_change()
    
    @property
    def current_state(self) -> TaskState:
        """获取当前状态"""
        return self._current_state
    
    def can_transition_to(self, target_state: TaskState) -> bool:
        """
        检查是否可以转移到目标状态
        
        Args:
            target_state: 目标状态
            
        Returns:
            True如果转移合法，False否则
        """
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, [])
    
    def transition_to(self, target_state: TaskState, reason: str = "") -> bool:
        """
        尝试转移到新状态
        
        Args:
            target_state: 目标状态
            reason: 转移原因（用于日志）
            
        Returns:
            True转移成功，False转移失败
        """
        if not self.can_transition_to(target_state):
            return False
        
        old_state = self._current_state
        self._current_state = target_state
        self._record_state_change()
        
        return True
    
    def _record_state_change(self):
        """记录状态变化（用于调试和审计）"""
        import time
        self._state_history.append((time.time(), self._current_state))
    
    def get_history(self) -> List[tuple]:
        """获取状态变化历史"""
        return self._state_history.copy()
    
    def reset(self):
        """
        重置状态机到Idle
        
        用于任务完成后准备下一个任务
        """
        self._current_state = TaskState.IDLE
        self._record_state_change()
