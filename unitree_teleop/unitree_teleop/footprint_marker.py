import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Point, PolygonStamped, PoseStamped
from visualization_msgs.msg import Marker, MarkerArray


class FootprintMarker(Node):
    def __init__(self):
        super().__init__('go2_footprint_marker')

        self.publisher = self.create_publisher(
            Marker, '/go2/footprint_marker', 10
        )
        self.subscription = self.create_subscription(
            PolygonStamped,
            '/local_costmap/published_footprint',
            self.footprint_callback,
            10
        )

        self.goal_tolerance = 0.25
        self.goal_publisher = self.create_publisher(
            MarkerArray,
            '/go2/goal_tolerance_marker_array',
            10
        )
        self.goal_subscription = self.create_subscription(
            PoseStamped,
            '/goal_pose',
            self.goal_callback,
            10
        )

        self.get_logger().info(
            'Footprint- und Zieltoleranz-Visualisierung gestartet.'
        )

    def footprint_callback(self, msg):
        if len(msg.polygon.points) < 3:
            return

        marker = Marker()
        marker.header = msg.header
        marker.ns = 'go2_footprint'
        marker.id = 0
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0

        marker.scale.x = 0.03

        marker.color.r = 0.0
        marker.color.g = 1.0
        marker.color.b = 0.2
        marker.color.a = 1.0

        for p in list(msg.polygon.points) + [msg.polygon.points[0]]:
            point = Point()
            point.x = float(p.x)
            point.y = float(p.y)
            point.z = 0.02
            marker.points.append(point)

        self.publisher.publish(marker)

    def goal_callback(self, msg):
        diameter = 2.0 * self.goal_tolerance
        marker_array = MarkerArray()

        disk = Marker()
        disk.header = msg.header
        disk.ns = 'go2_goal_tolerance'
        disk.id = 0
        disk.type = Marker.CYLINDER
        disk.action = Marker.ADD
        disk.pose.position.x = msg.pose.position.x
        disk.pose.position.y = msg.pose.position.y
        disk.pose.position.z = 0.005
        disk.pose.orientation.w = 1.0
        disk.scale.x = diameter
        disk.scale.y = diameter
        disk.scale.z = 0.01
        disk.color.r = 0.1
        disk.color.g = 1.0
        disk.color.b = 0.1
        disk.color.a = 0.12
        marker_array.markers.append(disk)

        ring = Marker()
        ring.header = msg.header
        ring.ns = 'go2_goal_tolerance'
        ring.id = 1
        ring.type = Marker.LINE_STRIP
        ring.action = Marker.ADD
        ring.pose.position.x = msg.pose.position.x
        ring.pose.position.y = msg.pose.position.y
        ring.pose.orientation.w = 1.0
        ring.scale.x = 0.025
        ring.color.r = 0.1
        ring.color.g = 1.0
        ring.color.b = 0.1
        ring.color.a = 0.95

        segments = 72
        for index in range(segments + 1):
            angle = 2.0 * math.pi * index / segments
            point = Point()
            point.x = self.goal_tolerance * math.cos(angle)
            point.y = self.goal_tolerance * math.sin(angle)
            point.z = 0.025
            ring.points.append(point)

        marker_array.markers.append(ring)
        self.goal_publisher.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)
    node = FootprintMarker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
