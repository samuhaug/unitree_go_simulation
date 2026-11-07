import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Point, PolygonStamped
from visualization_msgs.msg import Marker


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

        self.get_logger().info('Footprint-Visualisierung gestartet.')

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
