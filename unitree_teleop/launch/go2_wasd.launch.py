#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():

    description_share = get_package_share_directory(
        "unitree_description"
    )

    teleop_share = get_package_share_directory(
        "unitree_teleop"
    )

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(
                Path(description_share)
                / "launch"
                / "simulation.launch.py"
            )
        )
    )

    champ_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(
                Path(teleop_share)
                / "launch"
                / "champ.launch.py"
            )
        )
    )

    adapter = Node(
        package="unitree_teleop",
        executable="champ_manual_adapter",
        name="champ_manual_adapter",
        output="screen",
    )

    control_mux = Node(
        package="unitree_teleop",
        executable="control_mux",
        name="go2_control_mux",
        output="screen",
    )

    return LaunchDescription([
        gazebo_launch,
        champ_launch,
        control_mux,
        adapter,
    ])
