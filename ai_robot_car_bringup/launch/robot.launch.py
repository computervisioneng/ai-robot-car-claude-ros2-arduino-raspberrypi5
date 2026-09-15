from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition


def generate_launch_description():

    teleop_node = DeclareLaunchArgument('teleop_node', default_value='false')

    nodes = [
        Node(
            package="robot_car",
            executable="teleop_robot_node",
            prefix="xterm -e",
            condition=IfCondition(LaunchConfiguration('teleop_node'))
        ),
        Node(
            package="robot_car",
            executable="robot_controller_node"
        ),
        Node(
            package="robot_car",
            executable="computer_vision_engine_node",
            condition=UnlessCondition(LaunchConfiguration('teleop_node'))
        ),
        Node(
            package="robot_car",
            executable="behaviour_controller_node",
            parameters=[{'mode': 'hide_and_seek'}],
            condition=UnlessCondition(LaunchConfiguration('teleop_node'))
        )
    ]

    return LaunchDescription([teleop_node] + nodes)
