"""
ROS2 Launch文件 - 机器人任务管理系统启动配置

这个文件展示如何使用ROS2标准的Launch系统启动系统。
与run.sh的区别：
  - run.sh: 普通Bash脚本，需要菜单交互
  - Launch: ROS2原生系统，可同时启动多个节点

使用方式:
  ros2 launch py_pubsub robot_system.launch.py

设计理由：
  - 标准化：遵循ROS2最佳实践
  - 灵活性：支持参数化和条件启动
  - 可维护性：集中管理所有节点配置
  - 可扩展性：易于添加新节点或工具
"""

from launch import LaunchDescription
from launch.launch_context import LaunchContext
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """
    生成启动描述
    
    Returns:
        LaunchDescription: 包含所有节点和配置的启动描述
    """
    
    # 声明启动参数（可通过命令行传入）
    # 例如: ros2 launch py_pubsub robot_system.launch.py simulation_mode:=true
    declare_simulation_arg = DeclareLaunchArgument(
        'simulation_mode',
        default_value='true',
        description='是否使用模拟模式（true）或真实导航（false）'
    )
    
    declare_nav_timeout_arg = DeclareLaunchArgument(
        'nav_timeout',
        default_value='20.0',
        description='导航超时时间（秒）'
    )
    
    declare_log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='日志级别 (debug|info|warn|error)'
    )
    
    # 任务管理器节点
    # 这是系统的核心，负责任务创建和状态管理
    task_manager_node = Node(
        package='py_pubsub',
        executable='task_manager_node',
        name='task_manager',
        
        # 将日志输出到屏幕（便于调试）
        # output='log' 将输出到日志文件
        output='screen',
        
        # 参数配置（这些会传给节点）
        parameters=[
            {
                'simulation_mode': LaunchConfiguration('simulation_mode'),
                'nav_timeout': LaunchConfiguration('nav_timeout'),
            }
        ],
        
        # 话题重映射（如果需要）
        # 例如：将 /robot/goal_point 重映射为 /task_manager/goal_point
        # remappings=[('/robot/goal_point', '/task_manager/goal_point')],
        
        # 如果节点崩溃自动重启
        respawn=True,
        respawn_delay=2.0,
        
        # 环境变量（可选）
        # env={'ROS_LOG_DIR': '/tmp/ros_logs'},
    )
    
    # 目标点发布客户端节点（可选）
    # 注意：这个节点需要用户交互输入，所以在自动化场景中可能不适合
    # 可以通过命令行参数控制是否启动
    
    # 启动描述
    ld = LaunchDescription([
        # 声明所有参数
        declare_simulation_arg,
        declare_nav_timeout_arg,
        declare_log_level_arg,
        
        # 打印启动信息
        LogInfo(
            msg=[
                "========================================",
                "ROS2 机器人任务管理系统",
                "========================================",
                "模拟模式: ",
                LaunchConfiguration('simulation_mode'),
                "导航超时: ",
                LaunchConfiguration('nav_timeout'),
                "日志级别: ",
                LaunchConfiguration('log_level'),
                "========================================",
            ]
        ),
        
        # 添加节点
        task_manager_node,
    ])
    
    return ld


# 这是Launch系统的标准接口
# ROS2会自动调用这个函数来获取启动描述
