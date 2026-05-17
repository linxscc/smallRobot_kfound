"""
任务发布客户端

功能：向任务管理器发送多点位任务
用法：python3 -m py_pubsub.client

支持两种使用方式：
1. 创建单点位任务: 直接输入坐标 "5 5"
2. 创建多点位任务: 输入一个或多个路径点 "x1 y1 | x2 y2 | ..."

示例：
  单点位: 5 5
  多点位: 0 0 | 5 5 | 10 10
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json


class TaskPublisherClient(Node):
    """发布多点位任务的客户端节点"""
    
    def __init__(self):
        super().__init__('task_publisher_client')
        
        # 创建发布者
        self.publisher = self.create_publisher(
            String,
            '/robot/goal_point',
            10
        )
        
        self.get_logger().info("任务发布客户端已启动")
        self.logger = self.get_logger()
    
    def publish_task(self, waypoints: list, task_id: str = None):
        """
        发布多点位任务
        
        Args:
            waypoints: 路径点列表，每个元素为 {"x": float, "y": float, ...}
            task_id: 可选的任务ID
        """
        msg = String()
        task_data = {"waypoints": waypoints}
        
        if task_id:
            task_data["task_id"] = task_id
        
        msg.data = json.dumps(task_data)
        self.publisher.publish(msg)
        
        self.logger.info(f"已发布任务，共{len(waypoints)}个路径点")
        for i, wp in enumerate(waypoints, 1):
            x = wp.get('x', 0)
            y = wp.get('y', 0)
            name = wp.get('name', f"Point{i}")
            self.logger.info(f"  #{i} {name}: ({x}, {y})")


def main(args=None):
    """主函数"""
    rclpy.init(args=args)
    
    client = TaskPublisherClient()

    print("\n" + "="*50)
    print(("  多点位任务发布客户端").center(50))
    print("="*50 + "\n")
    
    print("使用说明:")
    print("  单点位: 输入 '5 5' -> 创建到(5,5)的单点位任务")
    print("  多点位: 输入 '0 0 | 5 5 | 10 10' -> 创建3个路径点的任务")
    print("  退出  : 输入 'quit' 或 'exit'")
    print()

    try:
        while True:
            user_input = input("输入任务 > ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print("再见！")
                break
            
            try:
                # 检查是否包含多点位分隔符
                waypoints = []
                
                if '|' in user_input:
                    # 多点位任务
                    parts = user_input.split('|')
                    for i, part in enumerate(parts):
                        coords = part.strip().split()
                        if len(coords) < 2:
                            print("❌ 格式错误，每个点至少需要两个坐标")
                            raise ValueError("Invalid format")
                        
                        x = float(coords[0])
                        y = float(coords[1])
                        waypoints.append({
                            'x': x,
                            'y': y,
                            'name': f'Point{i+1}',
                            'timeout': 20.0
                        })
                else:
                    # 单点位任务（转换为多点位格式）
                    parts = user_input.split()
                    if len(parts) < 2:
                        print("❌ 格式错误，请输入至少两个坐标值")
                        continue
                    
                    x = float(parts[0])
                    y = float(parts[1])
                    waypoints.append({
                        'x': x,
                        'y': y,
                        'name': 'Target',
                        'timeout': 20.0
                    })
                
                # 发布任务
                client.publish_task(waypoints)
                print(f"✓ 任务已发送（{len(waypoints)}个路径点）\n")
                
            except (ValueError, IndexError):
                print("❌ 请输入有效的坐标")
                print("   示例: '5 5' 或 '0 0 | 5 5 | 10 10'\n")
    
    except KeyboardInterrupt:
        print("\n程序中止")
    finally:
        client.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
