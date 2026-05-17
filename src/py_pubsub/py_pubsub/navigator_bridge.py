"""
导航桥接模块

功能：隔离任务管理器与底层导航栈的细节
设计理由：
  - 使用适配器模式，便于未来切换真实导航框架
  - 当前实现Mock导航（模拟机器人运动）
  - 提供异步导航结果回调，支持实时反馈
  - 易于集成Nav2堆栈（ROS2官方导航框架）
"""

import threading
import time
import random
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

from .logger_module import get_logger


class NavigationStatus(Enum):
    """导航状态"""
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass
class GoalPoint:
    """目标点数据结构"""
    x: float
    y: float
    theta: float = 0.0  # 方向角
    
    def __repr__(self):
        return f"GoalPoint(x={self.x}, y={self.y}, theta={self.theta})"


@dataclass
class NavigationResult:
    """导航结果"""
    success: bool              # 是否成功
    message: str               # 结果信息
    distance_traveled: float = 0.0  # 走过的距离（Mock用）


class NavigatorBridge:
    """
    导航桥接器
    
    作为任务管理器与导航底层的中介。
    当前使用Mock实现进行演示，可后续替换为真实Nav2调用。
    """
    
    def __init__(self):
        """初始化导航桥接器"""
        self.logger = get_logger("NavigatorBridge")
        self.status = NavigationStatus.IDLE
        self._current_goal: Optional[GoalPoint] = None
        self._result_callback: Optional[Callable] = None
        self._navigation_thread: Optional[threading.Thread] = None
        
        self.logger.info("导航桥接器初始化完成")
    
    def send_goal(self, goal: GoalPoint, result_callback: Callable) -> bool:
        """
        发送导航目标
        
        Args:
            goal: 目标点
            result_callback: 导航完成时的回调函数，签名：callback(result: NavigationResult)
            
        Returns:
            True表示成功接受目标，False表示失败（如正在导航中）
        """
        if self.status == NavigationStatus.NAVIGATING:
            self.logger.warn(f"导航器正在运行中，无法接受新目标")
            return False
        
        self._current_goal = goal
        self._result_callback = result_callback
        self.status = NavigationStatus.NAVIGATING
        
        self.logger.info(f"接收导航目标: {goal}")
        
        # 启动异步导航线程（模拟导航过程）
        self._navigation_thread = threading.Thread(
            target=self._navigate_mock,
            daemon=True
        )
        self._navigation_thread.start()
        
        return True
    
    def _navigate_mock(self):
        """
        模拟导航过程（Mock实现）
        
        在真实环境中，这里会调用Nav2的Action客户端。
        
        设计理由：
          - 不需要真实硬件即可测试整个系统
          - 可以设置失败概率用于测试异常处理
          - 便于演示和快速迭代
        """
        try:
            # 模拟导航时间（1-3秒）
            nav_time = random.uniform(1, 3)
            self.logger.debug(f"开始模拟导航，预计耗时 {nav_time:.1f} 秒...")
            
            # 计数进度（每0.5秒打印一次）
            elapsed = 0
            while elapsed < nav_time:
                time.sleep(0.5)
                elapsed += 0.5
                progress = int((elapsed / nav_time) * 100)
                self.logger.debug(f"导航进度: {progress}%")
            
            # 90%概率成功，10%概率失败（用于测试异常处理）
            success = random.random() < 0.9
            
            if success:
                self.status = NavigationStatus.SUCCEEDED
                result = NavigationResult(
                    success=True,
                    message="导航成功！机器人已到达目标点",
                    distance_traveled=random.uniform(5, 15)
                )
                self.logger.info(f"导航完成: {result.message}")
            else:
                self.status = NavigationStatus.FAILED
                result = NavigationResult(
                    success=False,
                    message="导航失败！检测到障碍物或路径规划错误"
                )
                self.logger.warn(f"导航失败: {result.message}")
            
            # 触发结果回调
            if self._result_callback:
                self._result_callback(result)
                
        except Exception as e:
            self.logger.error(f"导航过程发生异常: {str(e)}")
            self.status = NavigationStatus.FAILED
            if self._result_callback:
                result = NavigationResult(
                    success=False,
                    message=f"导航异常: {str(e)}"
                )
                self._result_callback(result)
    
    def cancel_goal(self) -> bool:
        """
        取消当前导航目标
        
        Returns:
            True表示成功取消，False表示没有目标可取消
        """
        if self.status != NavigationStatus.NAVIGATING:
            self.logger.warn("当前没有正在执行的导航")
            return False
        
        self.status = NavigationStatus.IDLE
        self._current_goal = None
        self.logger.info("导航目标已取消")
        return True
    
    def get_status(self) -> NavigationStatus:
        """获取当前导航状态"""
        return self.status
    
    def wait_for_result(self, timeout: float = 10.0) -> Optional[NavigationResult]:
        """
        等待导航结果（阻塞调用）
        
        Args:
            timeout: 最大等待时间（秒）
            
        Returns:
            导航结果，如果超时则返回None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.status in [NavigationStatus.SUCCEEDED, NavigationStatus.FAILED]:
                return self._current_goal
            time.sleep(0.1)
        
        self.logger.warn(f"等待导航结果超时（{timeout}秒）")
        return None
