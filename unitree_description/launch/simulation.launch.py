import os
import xacro


from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import ExecuteProcess, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit


def generate_launch_description():
    package_share = get_package_share_directory('unitree_description')
    world_file = os.path.join(package_share, 'worlds', 'go2_world.sdf')
    xacro_file = os.path.join(package_share, 'urdf', 'unitree_go2_robot.xacro')   
    anchor_file = os.path.join(package_share, 'worlds', 'go2_anchor.sdf')
    robot_description = xacro.process_file(xacro_file).toxml()   
    gazebo_env = os.environ.copy()
    resource_path = os.path.dirname(package_share)
    existing_resource_path = gazebo_env.get('GZ_SIM_RESOURCE_PATH', '')

    if existing_resource_path:
        resource_path += os.pathsep + existing_resource_path

    gazebo_env['GZ_SIM_RESOURCE_PATH'] = resource_path

    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_file],
        additional_env=gazebo_env,
        output='screen',
    )
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen',
    )
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen',
    )

    spawn_anchor = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-world', 'go2_world',
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
            '-y', '-1.0',
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
            on_exit=[
                TimerAction(
                    period=1.0,
                    actions=[detach_command],
                )
            ],
        )
    )
    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        clock_bridge,
        spawn_anchor,
        spawn_robot_after_anchor,
        joint_state_broadcaster_spawner,
        leg_position_controller_spawner,
        stand_after_controller,
        detach_after_stand,
    ])
