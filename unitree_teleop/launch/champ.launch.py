#!/usr/bin/env python3

import os
from pathlib import Path

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    root = Path(
        os.environ.get(
            "UNITREE_GO2_CHAMP_ROOT",
            str(Path.home() / "go2_references/unitree_go2_ros2"),
        )
    ).expanduser()

    config = root / "unitree_go2_sim/config"
    model = root / "unitree_go2_description/urdf/unitree_go2_robot.xacro"

    # Xacro in eine URDF-Zeichenkette umwandeln
    import xacro
    robot_description = xacro.process_file(str(model)).toxml()

    return LaunchDescription([
        Node(
            package="champ_base",
            executable="quadruped_controller_node",
            name="quadruped_controller_node",
            output="screen",
            parameters=[
                {"gazebo": True},
                {"publish_joint_states": False},
                {"publish_joint_control": True},
                {"publish_foot_contacts": False},
                {"joint_controller_topic": "/champ/joint_trajectory"},
                {"urdf": robot_description},
                {"use_sim_time": False},
                str(config / "joints/joints.yaml"),
                str(config / "links/links.yaml"),
                str(config / "gait/gait.yaml"),
            ],
            remappings=[
                ("/cmd_vel/smooth", "/champ/cmd_vel"),
            ],
        ),
    ])
