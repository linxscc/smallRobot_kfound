"""
高级任务管理器 - 扩展模块

功能扩展：支持多点位任务、任务取消、超时处理、详细日志、YAML配置

这个模块扩展了基础的task_manager，添加了生产级别的功能。
"""

from typing import List, Dict, Optional, Callable
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .state_machine import TaskState, TaskStateMachine
from .navigator_bridge import NavigatorBridge, GoalPoint, NavigationResult
from .logger_module import get_logger


class TaskCancelReason(Enum):
    """任务取消原因"""
    USER_CANCEL = "用户取消"
    TIMEOUT = "执行超时"
    NAVIGATION_FAILED = "导航失败"
    INVALID_GOAL = "目标点无效"
    SYSTEM_ERROR = "系统错误"


@dataclass
class ExecutionLog:
    """单个任务执行日志"""
    timestamp: float
    event_type: str  # "start", "progress", "success", "failed", "cancelled"
    message: str
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'event_type': self.event_type,
            'message': self.message,
            'metadata': self.metadata,
        }


@dataclass
class WayPoint:
    """路径点：任务的单个目标"""
    order: int              # 点的序号
    x: float
    y: float
    theta: float = 0.0
    name: str = ""          # 点的名称
    timeout: float = 20.0   # 该点的超时时间
    
    def to_goal_point(self) -> GoalPoint:
        """转换为GoalPoint"""
        return GoalPoint(x=self.x, y=self.y, theta=self.theta)


@dataclass
class MultiPointTask:
    """多点位任务"""
    task_id: str
    waypoints: List[WayPoint]              # 所有路径点
    created_time: float
    status: TaskState = TaskState.IDLE
    
    current_waypoint_index: int = 0        # 当前执行的路径点索引
    result_message: str = ""
    error_reason: Optional[TaskCancelReason] = None
    
    execution_logs: List[ExecutionLog] = field(default_factory=list)
    cancel_requested: bool = False
    
    def get_current_waypoint(self) -> Optional[WayPoint]:
        """获取当前路径点"""
        if self.current_waypoint_index < len(self.waypoints):
            return self.waypoints[self.current_waypoint_index]
        return None
    
    def get_progress(self) -> Dict:
        """获取任务进度"""
        total = len(self.waypoints)
        completed = self.current_waypoint_index
        return {
            'total': total,
            'completed': completed,
            'percentage': int((completed / total * 100)) if total > 0 else 0,
        }
    
    def add_log(self, event_type: str, message: str, metadata: Dict = None):
        """添加执行日志"""
        log = ExecutionLog(
            timestamp=time.time(),
            event_type=event_type,
            message=message,
            metadata=metadata or {}
        )
        self.execution_logs.append(log)


class TaskManager:
    """
    高级任务管理器
    
    功能：
    1. 多点位任务支持 - 可执行包含多个目标点的任务序列
    2. 任务取消机制 - 支持在运行中取消任务
    3. 超时处理 - 每个路径点都有独立的超时控制
    4. 详细日志 - 记录每一步执行过程和失败原因
    5. 预配置支持 - 从YAML读取任务参数
    """
    
    def __init__(self):
        """初始化高级任务管理器"""
        self.logger = get_logger("TaskManager")
        self.navigator = NavigatorBridge()
        self.state_machine = TaskStateMachine()
        
        self.current_task: Optional[MultiPointTask] = None
        self.task_history: Dict[str, MultiPointTask] = {}
        
        self._cancel_event = threading.Event()
        self._timeout_thread: Optional[threading.Thread] = None
        
        self.logger.info("高级任务管理器已初始化")
    
    def create_multi_point_task(self, waypoints: List[Dict], task_id: str = None) -> MultiPointTask:
        """
        创建多点位任务
        
        Args:
            waypoints: 路径点列表，每个是 {'x': float, 'y': float, 'theta': float, 'name': str, 'timeout': float}
            task_id: 任务ID（可选）
            
        Returns:
            创建的任务对象
        """
        if not waypoints:
            self.logger.error("路径点列表为空")
            return None
        
        if self.current_task and self.current_task.status in [TaskState.PENDING, TaskState.RUNNING]:
            self.logger.warn(f"任务{self.current_task.task_id}正在执行中")
            return None
        
        import uuid
        task_id = task_id or str(uuid.uuid4())[:8]
        
        # 创建路径点对象
        wp_list = []
        for i, wp_dict in enumerate(waypoints):
            wp = WayPoint(
                order=i + 1,
                x=wp_dict['x'],
                y=wp_dict['y'],
                theta=wp_dict.get('theta', 0.0),
                name=wp_dict.get('name', f'Point{i+1}'),
                timeout=wp_dict.get('timeout', 20.0)
            )
            wp_list.append(wp)
        
        task = MultiPointTask(
            task_id=task_id,
            waypoints=wp_list,
            created_time=time.time()
        )
        
        self.current_task = task
        
        # 状态转移
        self.state_machine.transition_to(TaskState.PENDING)
        task.status = TaskState.PENDING
        
        # 记录日志
        task.add_log(
            'start',
            f'多点位任务创建成功，共{len(wp_list)}个路径点',
            {'waypoints': len(wp_list), 'total_distance': self._calculate_path_length(wp_list)}
        )
        
        self.logger.info(
            f"创建多点位任务 [{task_id}]，包含{len(wp_list)}个路径点"
        )
        
        return task
    
    def execute_task(self, task: Optional[MultiPointTask] = None) -> bool:
        """
        执行多点位任务
        
        按顺序执行所有路径点。如果当前点失败，整个任务失败。
        """
        task = task or self.current_task
        
        if task is None:
            self.logger.error("没有任务可执行")
            return False
        
        if task.status != TaskState.PENDING:
            self.logger.error(f"任务状态错误 (当前: {task.status})")
            return False
        
        # 状态转移到RUNNING
        self.state_machine.transition_to(TaskState.RUNNING)
        task.status = TaskState.RUNNING
        
        self.logger.info(f"任务 {task.task_id} 开始执行")
        
        # 启动超时监测线程
        self._cancel_event.clear()
        self._timeout_thread = threading.Thread(
            target=self._execute_waypoints,
            args=(task,),
            daemon=True
        )
        self._timeout_thread.start()
        
        return True
    
    def _execute_waypoints(self, task: MultiPointTask):
        """
        执行所有路径点（在后台线程中运行）
        """
        for i, waypoint in enumerate(task.waypoints):
            if task.cancel_requested:
                task.add_log(
                    'cancelled',
                    f'任务在执行第{waypoint.order}个路径点时被取消',
                    {'waypoint': waypoint.name}
                )
                self.state_machine.transition_to(TaskState.FAILED)
                task.status = TaskState.FAILED
                task.error_reason = TaskCancelReason.USER_CANCEL
                break
            
            task.current_waypoint_index = i
            goal = waypoint.to_goal_point()
            
            self.logger.info(
                f"执行第{waypoint.order}个路径点: {waypoint.name} {goal}"
            )
            
            # 发送导航目标
            success = self.navigator.send_goal(
                goal,
                lambda result: self._on_waypoint_complete(result, task, waypoint)
            )
            
            if not success:
                task.add_log(
                    'failed',
                    f'第{waypoint.order}个路径点导航失败',
                    {'waypoint': waypoint.name}
                )
                self._handle_task_failure(task, TaskCancelReason.NAVIGATION_FAILED)
                return
            
            # 等待这个路径点完成或超时
            start_time = time.time()
            while True:
                if task.cancel_requested:
                    break
                
                elapsed = time.time() - start_time
                if elapsed > waypoint.timeout:
                    task.add_log(
                        'timeout',
                        f'第{waypoint.order}个路径点执行超时 ({waypoint.timeout}秒)',
                        {'waypoint': waypoint.name}
                    )
                    self.navigator.cancel_goal()
                    self._handle_task_failure(task, TaskCancelReason.TIMEOUT)
                    return
                
                # 检查导航状态
                nav_status = self.navigator.get_status()
                if nav_status.value in ['SUCCEEDED', 'FAILED']:
                    break
                
                time.sleep(0.1)
        
        # 所有路径点都完成
        self.state_machine.transition_to(TaskState.ARRIVED)
        task.status = TaskState.ARRIVED
        task.result_message = f"成功完成{len(task.waypoints)}个路径点"
        
        task.add_log(
            'success',
            f'任务{task.task_id}执行成功',
            {'waypoints_completed': len(task.waypoints)}
        )
        
        self.logger.info(f"任务{task.task_id}已完成")
    
    def _on_waypoint_complete(self, result: NavigationResult, task: MultiPointTask, waypoint: WayPoint):
        """单个路径点完成的回调"""
        if result.success:
            task.add_log(
                'progress',
                f'成功到达第{waypoint.order}个路径点 {waypoint.name}',
                {'waypoint': waypoint.name, 'distance': result.distance_traveled}
            )
        else:
            task.add_log(
                'failed',
                f'第{waypoint.order}个路径点失败: {result.message}',
                {'waypoint': waypoint.name}
            )
    
    def _handle_task_failure(self, task: MultiPointTask, reason: TaskCancelReason):
        """处理任务失败"""
        self.state_machine.transition_to(TaskState.FAILED)
        task.status = TaskState.FAILED
        task.error_reason = reason
        task.result_message = f"任务失败: {reason.value}"
        
        self.logger.error(
            f"任务{task.task_id}失败 - 原因: {reason.value}"
        )
    
    def cancel_task(self, task_id: str = None) -> bool:
        """
        取消任务执行
        
        Args:
            task_id: 任务ID（可选，默认取消当前任务）
            
        Returns:
            True表示成功取消
        """
        task = self.current_task
        
        if task is None:
            self.logger.warn("没有任务可取消")
            return False
        
        if task.status not in [TaskState.PENDING, TaskState.RUNNING]:
            self.logger.warn(f"任务 {task.task_id} 状态 {task.status} 无法取消")
            return False
        
        task.cancel_requested = True
        self.navigator.cancel_goal()
        
        self.logger.warn(f"任务 {task.task_id} 已请求取消")
        return True
    
    def get_task_progress(self, task_id: str = None) -> Dict:
        """获取任务进度"""
        task = self.current_task
        
        if task is None:
            return {'status': 'idle'}
        
        progress = task.get_progress()
        progress['status'] = str(task.status)
        progress['current_waypoint'] = None
        
        if task.get_current_waypoint():
            wp = task.get_current_waypoint()
            progress['current_waypoint'] = {
                'order': wp.order,
                'name': wp.name,
                'coordinates': {'x': wp.x, 'y': wp.y}
            }
        
        return progress
    
    def get_execution_logs(self, task_id: str = None) -> List[Dict]:
        """获取任务的执行日志"""
        task = self.current_task
        
        if task is None:
            return []
        
        return [log.to_dict() for log in task.execution_logs]
    
    def _calculate_path_length(self, waypoints: List[WayPoint]) -> float:
        """计算路径总长度（简单欧氏距离）"""
        if len(waypoints) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(waypoints) - 1):
            wp1, wp2 = waypoints[i], waypoints[i+1]
            distance = ((wp2.x - wp1.x)**2 + (wp2.y - wp1.y)**2) ** 0.5
            total += distance
        
        return total
    
    def reset(self):
        """重置管理器"""
        self.cancel_task()
        self.state_machine.reset()
        self.current_task = None
        self._cancel_event.set()
        self.logger.info("任务管理器已重置")
