import os
import xacro


from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit


def generate_launch_description():
    package_share = get_package_share_directory('unitree_description')
    xacro_file = os.path.join(package_share, 'urdf', 'unitree_go2_robot.xacro')   
    anchor_file = os.path.join(package_share, 'worlds', 'go2_anchor.sdf')
    robot_description = xacro.process_file(xacro_file).toxml()   
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen',
    )
    spawn_anchor = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-world', 'empty',
            '-file', anchor_file,
            '-name', 'go2_anchor',
        ],
        output='screen',
    )
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', '/robot_description',
            '-name', 'go2',
            '-z', '1.0',
        ],
        output='screen',
    )
    spawn_robot_after_anchor = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_anchor,
            on_exit=[spawn_robot],
        )
    )
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )

    leg_position_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['leg_position_controller'],
        output='screen',
    )

    stand_command = ExecuteProcess(
        cmd=[
            'ros2', 'topic', 'pub', '--once',
            '/leg_position_controller/commands',
            'std_msgs/msg/Float64MultiArray',
            '{data: [0.0, 0.8, -1.6, 0.0, 0.8, -1.6, 0.0, 0.8, -1.6, 0.0, 0.8, -1.6]}',
        ],
        output='screen',
    )

    detach_command = ExecuteProcess(
        cmd=[
            'gz', 'topic',
            '-t', '/go2/detach',
            '-m', 'gz.msgs.Empty',
            '-p', 'unused: true',
        ],
        output='screen',
    )

    stand_after_controller = RegisterEventHandler(
        OnProcessExit(
            target_action=leg_position_controller_spawner,
            on_exit=[stand_command],
        )
    )

    detach_after_stand = RegisterEventHandler(
        OnProcessExit(
            target_action=stand_command,
            on_exit=[detach_command],
        )
    )
    return LaunchDescription([
        robot_state_publisher,
        spawn_anchor,
        spawn_robot_after_anchor,
        joint_state_broadcaster_spawner,
        leg_position_controller_spawner,
        stand_after_controller,
        detach_after_stand,
    ])
