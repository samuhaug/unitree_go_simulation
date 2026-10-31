#!/usr/bin/env python3

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    teleop_share = Path(get_package_share_directory('unitree_teleop'))
    launch_dir = teleop_share / 'launch'

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(launch_dir / 'go2_wasd.launch.py')
        )
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(launch_dir / 'go2_bringup.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'use_composition': 'False',
            'slam': 'False',
            'map': str(teleop_share / 'maps' / 'go2_map_complete.yaml'),
            'params_file': str(
                teleop_share / 'config' / 'nav2_params.yaml'
            ),
        }.items(),
    )

    rviz_config = (
        Path(get_package_share_directory('unitree_description'))
        / 'rviz' / 'go2_navigation.rviz'
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', str(rviz_config)],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    return LaunchDescription([
        simulation,
        TimerAction(
            period=15.0,
            actions=[navigation, rviz],
        ),
    ])
