import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class SlamPoseBridge(Node):
    def __init__(self):
        super().__init__('slam_pose_bridge')
        self.set_parameters([rclpy.parameter.Parameter(
    		'use_sim_time',
    		rclpy.Parameter.Type.BOOL,
    		True
	)])
        self.tf_broadcaster = TransformBroadcaster(self)
        self.get_logger().info(
            'SLAM-Pose-Knoten gestartet. Warte auf Gazebo-Pose.'
        )

    def publish_transform(self, x, y, z, qx, qy, qz, qw):
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'trunk'

        transform.transform.translation.x = x
        transform.transform.translation.y = y
        transform.transform.translation.z = z

        transform.transform.rotation.x = qx
        transform.transform.rotation.y = qy
        transform.transform.rotation.z = qz
        transform.transform.rotation.w = qw

        self.tf_broadcaster.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = SlamPoseBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
