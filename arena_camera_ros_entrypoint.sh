#!/bin/bash

set -e
cd /arena_camera_ros2/ros2_ws 
#rosdep fix-permissions
#rosdep update
# rosdep install --from-paths src --ignore-src -r -y;
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

exec "$@"
