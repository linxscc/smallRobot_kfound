"""
ROS2 Launch文件 - 完整系统启动（多节点）

这个配置启动整个系统的所有组件，包括：
  1. 任务管理器节点（核心）
  2. 客户端节点（接收用户输入）
  
这展示了Launch系统的真正强大之处：
  - 同时启动多个节点
  - 统一配置和参数管理
  - 自动化启动和监控

使用方式:
  ros2 launch py_pubsub full_system.launch.py

对比shell脚本：
  shell脚本: 需要手动开启多个终端，分别运行各个节点
  launch: 一个命令启动所有节点
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo, Shutdown
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """
    生成完整系统的启动描述
    
    Returns:
        LaunchDescription: 包含所有节点的启动描述
    """
    
    # 启动参数声明
    declare_simulation_arg = DeclareLaunchArgument(
        'simulation',
        default_value='true',
        description='是否使用模拟模式'
    )
    
    declare_auto_start_arg = DeclareLaunchArgument(
        'auto_start_client',
        default_value='false',
        description='是否自动启动客户端节点（true需要交互输入比较烦人）'
    )
    
    # 任务管理器节点
    task_manager = Node(
        package='py_pubsub',
        executable='task_manager_node',
        name='task_manager_node',
        output='screen',
        
        parameters=[
            {'simulation_mode': LaunchConfiguration('simulation')},
        ],
        
        respawn=True,
        respawn_delay=3.0,
    )
    
    # 目标客户端节点（可选启动）
    goal_client = Node(
        package='py_pubsub',
        executable='client',
        name='goal_client_node',
        output='screen',
        
        # 这个节点需要交互输入，所以默认不启动
        # 如果要启动可以用: ros2 launch py_pubsub full_system.launch.py auto_start_client:=true
        condition=LaunchConfiguration('auto_start_client'),
    )
    
    # 构建启动描述
    return LaunchDescription([
        # 参数声明
        declare_simulation_arg,
        declare_auto_start_arg,
        
        # 启动信息
        LogInfo(
            msg=[
                "\n",
                "╔════════════════════════════════════════════════════╗",
                "║   ROS2 机器人任务管理系统 - 大型系统启动           ║",
                "║   Simulation Mode: ",
                LaunchConfiguration('simulation'),
                "║   Auto Start Client: ",
                LaunchConfiguration('auto_start_client'),
                "╚════════════════════════════════════════════════════╝",
                "\n",
            ]
        ),
        
        # 启动节点
        task_manager,
        goal_client,
        
        # 启动后的初始化命令（可选）
        # 例如：启动后自动发送一个demo任务
    ])
