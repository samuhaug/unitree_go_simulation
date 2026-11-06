cmake_minimum_required(VERSION 3.8)
project(unitree_teleop)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(PkgConfig REQUIRED)

pkg_check_modules(GZ_TRANSPORT REQUIRED IMPORTED_TARGET gz-transport13)

# Python-Paket installieren
ament_python_install_package(${PROJECT_NAME})

# C++-SLAM-Bridge
add_executable(slam_pose_bridge src/slam_pose_bridge.cpp)

ament_target_dependencies(slam_pose_bridge
  rclcpp
  geometry_msgs
  tf2_ros
)

target_link_libraries(slam_pose_bridge PkgConfig::GZ_TRANSPORT)

install(TARGETS
  slam_pose_bridge
  DESTINATION lib/${PROJECT_NAME}
)

# Python-Startskripte installieren
install(PROGRAMS
  scripts/go2_controller
  scripts/champ_manual_adapter
  scripts/wasd_teleop
  scripts/go2_motion_test
  scripts/control_mux
  scripts/odom_tf_bridge
  DESTINATION lib/${PROJECT_NAME}
)

# Launchdateien und SLAM-Konfiguration installieren
install(DIRECTORY
  launch
  config
  maps
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
