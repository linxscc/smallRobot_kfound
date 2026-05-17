"""
任务管理器ROS2节点（升级版） - 支持Unity可视化

支持数据发布：
  - 实时状态：位置、朝向、轨迹进度
  - 任务规划：完整路径点信息
  - 完整可视化：便于扩展
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
import time
import math

from .task_manager import TaskManager
from .config_manager import ConfigManager
from .logger_module import get_logger


class TaskManagerNode(Node):
    """
    升级后的任务管理器ROS2节点
    
    订阅话题：
      /robot/goal_point      - 接收多点位任务（waypoints格式）
      /robot/task_cancel     - 取消任务请求
      
    发布话题（任务相关）：
      /robot/task_status     - 任务状态更新
      /robot/task_result     - 任务完成结果
      /robot/task_logs       - 执行日志流
      
    发布话题（Unity可视化）：
      /robot/state           - 实时状态 (100ms) - 位置、朝向、进度
      /robot/task_plan       - 任务规划 (一次) - 完整路径点
      /robot/visualization   - 完整可视化数据 (100ms) - 可扩展字段
    """
    
    def __init__(self):
        """初始化ROS2节点"""
        super().__init__('task_manager_node')
        
        # 初始化系统组件
        self.task_manager = TaskManager()
        self.config_manager = ConfigManager()
        self.logger = get_logger("TaskManagerNode")
        
        # 内部状态跟踪
        self.last_published_task_id = None  # 用于检测新任务
        self.last_waypoint_index = -1      # 用于检测轨迹变化
        self.current_position = {"x": 0.0, "y": 0.0}  # 当前位置
        self.current_orientation = 0.0      # 当前朝向（度）
        
        # 创建订阅者：接收导航目标
        self.goal_subscription = self.create_subscription(
            String,
            '/robot/goal_point',
            self.goal_callback,
            10
        )
        
        # 创建订阅者：接收取消请求
        self.cancel_subscription = self.create_subscription(
            String,
            '/robot/task_cancel',
            self.cancel_callback,
            10
        )
        
        # 创建发布者：发布任务状态
        self.status_publisher = self.create_publisher(
            String,
            '/robot/task_status',
            10
        )
        
        # 创建发布者：发布任务结果
        self.result_publisher = self.create_publisher(
            String,
            '/robot/task_result',
            10
        )
        
        # 创建发布者：发布执行日志
        self.logs_publisher = self.create_publisher(
            String,
            '/robot/task_logs',
            10
        )
        
        # ===== Unity 可视化相关发布者 =====
        # 实时状态（100ms）
        self.state_publisher = self.create_publisher(
            String,
            '/robot/state',
            10
        )
        
        # 任务规划（一次性）
        self.task_plan_publisher = self.create_publisher(
            String,
            '/robot/task_plan',
            10
        )
        
        # 完整可视化数据（100ms）- 可扩展
        self.visualization_publisher = self.create_publisher(
            String,
            '/robot/visualization',
            10
        )
        
        # 创建定时器：任务状态发布（2秒）
        self.timer = self.create_timer(2.0, self.timer_callback)
        
        # 创建定时器：Unity可视化数据发布（100ms = 10Hz）
        self.state_timer = self.create_timer(0.1, self.publish_state_callback)
        
        self.logger.info("升级后的任务管理器ROS2节点已启动")
        self.logger.info("订阅话题: /robot/goal_point, /robot/task_cancel")
        self.logger.info("发布话题 (任务): /robot/task_status, /robot/task_result, /robot/task_logs")
        self.logger.info("发布话题 (Unity): /robot/state, /robot/task_plan, /robot/visualization")
    
    def goal_callback(self, msg: String):
        """
        接收多点位任务请求
        
        消息格式：
        {
          "task_id": "task_001",  (可选)
          "waypoints": [
            {"x": 0, "y": 0, "name": "point_1", "timeout": 20},
            {"x": 10, "y": 10, "name": "point_2", "timeout": 25}
          ]
        }
        
        单点位任务示例（只需1个waypoint）：
        {
          "waypoints": [{"x": 5, "y": 5}]
        }
        
        Args:
            msg: 包含多点位任务的消息，格式为JSON字符串
        """
        try:
            goal_data = json.loads(msg.data)
            
            # 验证waypoints存在
            if 'waypoints' not in goal_data:
                self.logger.error("消息格式错误: 缺少 'waypoints' 字段")
                return
            
            waypoints = goal_data.get('waypoints', [])
            task_id = goal_data.get('task_id', None)
            
            if not waypoints:
                self.logger.error("waypoints 列表为空")
                return
            
            # 记录任务信息
            self.logger.info(f"收到任务请求，共{len(waypoints)}个路径点")
            for wp in waypoints:
                name = wp.get('name', f"Point({wp.get('x', 0)}, {wp.get('y', 0)})")
                timeout = wp.get('timeout', 20.0)
                self.logger.debug(f"  路径点: {name}, 超时: {timeout}s")
            
            # 创建多点位任务
            task = self.task_manager.create_multi_point_task(waypoints, task_id)
            
            if task:
                if self.task_manager.execute_task(task):
                    self.logger.info(f"任务{task.task_id}已开始执行")
                    # 发布任务规划到Unity
                    self.publish_task_plan(task)
                else:
                    self.logger.error(f"任务{task.task_id}执行失败")
            else:
                self.logger.warn("无法创建任务（可能有任务正在执行）")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"处理任务请求时发生错误: {str(e)}")
    
    def cancel_callback(self, msg: String):
        """
        接收取消任务的请求
        
        Args:
            msg: 包含取消信息的消息
                 {"task_id": str, "reason": str}
        """
        try:
            cancel_data = json.loads(msg.data)
            task_id = cancel_data.get('task_id')
            reason = cancel_data.get('reason', 'user_request')
            
            self.logger.warn(f"收到取消任务请求: {task_id}, 原因: {reason}")
            
            if self.task_manager.cancel_task(task_id):
                self.logger.warn(f"任务{task_id}已取消")
            else:
                self.logger.warn(f"无法取消任务{task_id}")
        
        except Exception as e:
            self.logger.error(f"处理取消请求时发生错误: {str(e)}")
    
    def timer_callback(self):
        """
        定时发布任务状态、结果和日志
        
        每2秒发布一次当前任务的完整信息
        """
        try:
            if self.task_manager.current_task is None:
                return
            
            task = self.task_manager.current_task
            
            # 1. 发布状态
            progress = self.task_manager.get_task_progress()
            status_msg = {
                'timestamp': time.time(),
                'task_id': task.task_id,
                'status': str(task.status),
                'progress': progress,
                'message': task.result_message or 'Task in progress'
            }
            
            msg = String()
            msg.data = json.dumps(status_msg)
            self.status_publisher.publish(msg)
            self.logger.debug(f"发布状态: {task.status}")
            
            # 2. 如果任务完成，发布结果和日志
            if str(task.status) in ['Arrived', 'Failed', 'ARRIVED', 'FAILED']:
                self._publish_task_result(task)
                self._publish_task_logs(task)
        
        except Exception as e:
            self.logger.error(f"发布信息时发生错误: {str(e)}")
    
    def _publish_task_result(self, task):
        """
        发布任务完成结果
        
        Args:
            task: MultiPointTask对象
        """
        result_status = str(task.status)
        
        result_msg = {
            'task_id': task.task_id,
            'final_status': result_status,
            'success': result_status == 'Arrived',
            'result_message': task.result_message,
            'error_reason': task.error_reason.value if task.error_reason else None,
            'execution_time': time.time() - task.created_time,
            'waypoints_completed': task.current_waypoint_index,
            'total_waypoints': len(task.waypoints),
            'timestamp': time.time()
        }
        
        msg = String()
        msg.data = json.dumps(result_msg)
        self.result_publisher.publish(msg)
        
        self.logger.info(f"发布任务结果: {result_status}")
    
    def _publish_task_logs(self, task):
        """
        发布任务执行日志
        
        Args:
            task: MultiPointTask对象
        """
        logs = self.task_manager.get_execution_logs()
        
        logs_msg = {
            'task_id': task.task_id,
            'total_logs': len(logs),
            'logs': logs,
            'timestamp': time.time()
        }
        
        msg = String()
        msg.data = json.dumps(logs_msg)
        self.logs_publisher.publish(msg)
        
        self.logger.info(f"发布{len(logs)}条执行日志")
    
    # ===== Unity 可视化相关方法 =====
    
    def publish_state_callback(self):
        """
        定时发布实时状态和完整可视化数据
        高频率（100ms）用于Unity实时显示
        """
        if self.task_manager.current_task is None:
            return
        
        try:
            task = self.task_manager.current_task
            
            # 更新模拟位置（实际应该从导航器获取）
            self.update_simulated_position(task)
            
            # 1. 发布实时状态 (/robot/state)
            self.publish_robot_state(task)
            
            # 2. 发布完整可视化数据 (/robot/visualization)
            self.publish_visualization_data(task)
            
        except Exception as e:
            self.logger.error(f"发布状态时出错: {str(e)}")
    
    def update_simulated_position(self, task):
        """
        更新机器人模拟位置
        实际系统中应该从实时导航系统获取
        """
        if not task.waypoints:
            return
        
        current_wp = task.get_current_waypoint()
        if not current_wp:
            return
        
        # 模拟：逐渐移动到当前目标点
        target_x = current_wp.x
        target_y = current_wp.y
        
        # 简单的线性插值
        dx = target_x - self.current_position['x']
        dy = target_y - self.current_position['y']
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 0.1:  # 如果距离大于0.1
            # 每100ms移动一点
            step = min(0.1, distance * 0.05)  # 5%的距离或最多0.1
            self.current_position['x'] += (dx / distance) * step
            self.current_position['y'] += (dy / distance) * step
        else:
            self.current_position = {'x': target_x, 'y': target_y}
        
        # 更新朝向（指向下一个目标）
        if distance > 0:
            self.current_orientation = math.degrees(math.atan2(dy, dx))
    
    def publish_robot_state(self, task):
        """
        发布机器人实时状态到 /robot/state
        
        消息格式：
        {
            "timestamp": float,
            "task_id": str,
            "position": {"x": float, "y": float},
            "orientation": float,           # 朝向角度 (-180到180)
            "current_waypoint_index": int,
            "total_waypoints": int,
            "task_status": str
        }
        """
        state_msg = {
            "timestamp": time.time(),
            "task_id": task.task_id,
            "position": self.current_position.copy(),
            "orientation": self.current_orientation,
            "current_waypoint_index": task.current_waypoint_index,
            "total_waypoints": len(task.waypoints),
            "task_status": str(task.status)
        }
        
        msg = String()
        msg.data = json.dumps(state_msg)
        self.state_publisher.publish(msg)
    
    def publish_task_plan(self, task):
        """
        发布任务规划信息到 /robot/task_plan
        
        消息格式：
        {
            "task_id": str,
            "waypoints": [
                {
                    "index": int,
                    "name": str,
                    "x": float,
                    "y": float,
                    "timeout": float
                }
            ],
            "total_distance": float
        }
        """
        # 计算总路程
        total_distance = 0.0
        if len(task.waypoints) > 1:
            for i in range(len(task.waypoints) - 1):
                wp1 = task.waypoints[i]
                wp2 = task.waypoints[i + 1]
                dx = wp2.x - wp1.x
                dy = wp2.y - wp1.y
                total_distance += math.sqrt(dx*dx + dy*dy)
        
        waypoints_list = [
            {
                "index": i,
                "name": wp.name,
                "x": wp.x,
                "y": wp.y,
                "timeout": wp.timeout
            }
            for i, wp in enumerate(task.waypoints)
        ]
        
        plan_msg = {
            "task_id": task.task_id,
            "waypoints": waypoints_list,
            "total_distance": total_distance
        }
        
        msg = String()
        msg.data = json.dumps(plan_msg)
        self.task_plan_publisher.publish(msg)
        self.logger.debug(f"发布任务规划: {task.task_id}")
    
    def publish_visualization_data(self, task):
        """
        发布完整可视化数据到 /robot/visualization
        包含所有Unity需要的信息，保留扩展字段
        
        消息格式：
        {
            "timestamp": float,
            "task_id": str,
            "robot": {
                "position": {"x": float, "y": float},
                "orientation": float,
                "status": str
            },
            "trajectory": {
                "current_waypoint_index": int,
                "total_waypoints": int,
                "waypoints": [{"x": float, "y": float, "name": str}]
            },
            "task": {
                "status": str,
                "progress": {"completed": int, "total": int},
                "message": str
            },
            "extensions": {}  # 保留扩展字段
        }
        """
        progress = self.task_manager.get_task_progress()
        
        # 构建路径点信息
        waypoints_info = [
            {
                "x": wp.x,
                "y": wp.y,
                "name": wp.name,
                "reached": i < task.current_waypoint_index
            }
            for i, wp in enumerate(task.waypoints)
        ]
        
        visualization_msg = {
            "timestamp": time.time(),
            "task_id": task.task_id,
            "robot": {
                "position": self.current_position.copy(),
                "orientation": self.current_orientation,
                "status": str(task.status)
            },
            "trajectory": {
                "current_waypoint_index": task.current_waypoint_index,
                "total_waypoints": len(task.waypoints),
                "waypoints": waypoints_info
            },
            "task": {
                "status": str(task.status),
                "progress": progress,
                "message": task.result_message or "Running"
            },
            "extensions": {
                # 保留扩展字段供后续使用
                "battery": None,
                "speed": None,
                "sensors": None
            }
        }
        
        msg = String()
        msg.data = json.dumps(visualization_msg)
        self.visualization_publisher.publish(msg)


def main(args=None):
    """
    ROS2节点主函数
    
    初始化ROS2通信并启动事件循环
    """
    rclpy.init(args=args)
    
    task_manager_node = TaskManagerNode()
    
    try:
        rclpy.spin(task_manager_node)
    except KeyboardInterrupt:
        pass
    finally:
        task_manager_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
