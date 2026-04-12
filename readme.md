初次构建项目
cd ~/projects/robot_project/smallRobot_kfound
source /opt/ros/jazzy/setup.bash
colcon build
给当前工作空间加环境
source install/setup.bash
用Python创建ROS 2 包
cd ~/projects/robot_project/smallRobot_kfound/src
ros2 pkg create --build-type ament_python py_pubsub
工作空间根目录编译项目
cd ~/projects/robot_project/smallRobot_kfound
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash