import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray


class Go2Controller(Node):

    def __init__(self):
        super().__init__('go2_controller')

        # Publisher für die zwölf Beingelenke
        self.joint_publisher = self.create_publisher(
            Float64MultiArray,
            '/leg_position_controller/commands',
            10
        )

        # Subscriber für Bewegungsbefehle
        self.cmd_vel_subscriber = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # Standposition für vier Beine mit je drei Gelenken
        self.stand_position = [
            0.0, 0.8, -1.6,
            0.0, 0.8, -1.6,
            0.0, 0.8, -1.6,
            0.0, 0.8, -1.6
        ]

        # Regelmäßig Standposition senden
        self.timer = self.create_timer(
            0.1,
            self.publish_stand_position
        )

        self.get_logger().info(
            'Go2 Controller gestartet. Warte auf /cmd_vel.'
        )

    def cmd_vel_callback(self, msg):
        self.get_logger().info(
            f'Bewegungsbefehl empfangen: '
            f'linear.x={msg.linear.x:.2f}, '
            f'angular.z={msg.angular.z:.2f}'
        )

    def publish_stand_position(self):
        msg = Float64MultiArray()
        msg.data = self.stand_position

        self.joint_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    node = Go2Controller()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
