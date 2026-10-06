from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    package_dir = get_package_share_directory('unitree_description')

    world = os.path.join(
        package_dir,
        'worlds',
        'go2_world.sdf'
    )

    robot_xacro = os.path.join(
        package_dir,
        'urdf',
        'unitree_go2_robot.xacro'
    )

    robot_description = os.popen(
        f'xacro "{robot_xacro}"'
    ).read()

    return LaunchDescription([
        ExecuteProcess(
            cmd=['gz', 'sim', world],
            output='screen'
        ),

        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'ros_gz_bridge',
                'parameter_bridge',
                '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan'
            ],
            output='screen'
        ),

        TimerAction(
            period=3.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        'gz', 'service',
                        '-s', '/world/go2_world/create',
                        '--reqtype', 'gz.msgs.EntityFactory',
                        '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '5000',
                        '--req',
                        f'sdf: {robot_description!r}, name: "go2", pose: {{position: {{z: 0.45}}}}'
                    ],
                    output='screen'
                )
            ]
        )
    ])
