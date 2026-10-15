import math
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64MultiArray


class Go2Controller(Node):

    def __init__(self):
        super().__init__('go2_controller')

        self.joint_publisher = self.create_publisher(
            Float64MultiArray,
            '/leg_position_controller/commands',
            10
        )

        self.cmd_vel_subscriber = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # Standposition aller vier Beine
        self.stand_position = [
            0.0, 0.8, -1.6,   # FL
            0.0, 0.8, -1.6,   # FR
            0.0, 0.8, -1.6,   # RL
            0.0, 0.8, -1.6    # RR
        ]

        # Beinlängen aus const.xacro
        self.thigh_length = 0.213
        self.calf_length = 0.213

        # Kleine Testbewegung
        self.step_height = 0.015   # 1,5 cm
        self.step_length = 0.020   # 2,0 cm
        self.step_duration = 3.0   # 3 Sekunden

        self.movement_active = False
        self.movement_start = None

        # Ausgangsposition des Fußes berechnen
        self.start_x, self.start_z = self.forward_kinematics(
            0.8, -1.6
        )

        self.timer = self.create_timer(
            0.1,
            self.update_controller
        )

        self.get_logger().info(
            'Go2 Controller gestartet. Warte auf /cmd_vel.'
        )

    def forward_kinematics(self, upper, lower):
        """Fußposition aus Gelenkwinkeln berechnen."""

        l1 = self.thigh_length
        l2 = self.calf_length

        x = -l1 * math.sin(upper) - l2 * math.sin(upper + lower)
        z = -l1 * math.cos(upper) - l2 * math.cos(upper + lower)

        return x, z

    def inverse_kinematics(self, x, z):
        """Gelenkwinkel für gewünschte Fußposition berechnen."""

        l1 = self.thigh_length
        l2 = self.calf_length

        distance_squared = x * x + z * z

        cos_knee = (
            distance_squared - l1 * l1 - l2 * l2
        ) / (2.0 * l1 * l2)

        # Numerische Rundungsfehler begrenzen
        cos_knee = max(-1.0, min(1.0, cos_knee))

        # Negative Kniebeugung wie in der Standposition
        lower = -math.acos(cos_knee)

        upper = (
            math.atan2(-x, -z)
            - math.atan2(
                l2 * math.sin(lower),
                l1 + l2 * math.cos(lower)
            )
        )

        return upper, lower

    def cmd_vel_callback(self, msg):
        """Ein Vorwärtsbefehl startet eine einzelne Testbewegung."""

        if msg.linear.x > 0.01 and not self.movement_active:
            self.movement_active = True
            self.movement_start = time.monotonic()

            self.get_logger().info(
                'Schrittbewegung gestartet.'
            )

        elif msg.linear.x <= 0.01 and self.movement_active:
            self.movement_active = False
            self.movement_start = None

            self.get_logger().info(
                'Bewegung gestoppt.'
            )

    def update_controller(self):
        positions = self.stand_position.copy()

        if self.movement_active:
            elapsed = time.monotonic() - self.movement_start

            if elapsed < self.step_duration:
                phase = elapsed / self.step_duration

                # Fuß anheben und wieder absenken
                lift = self.step_height * math.sin(
                    math.pi * phase
                )

                # Fuß vorwärts und zurück bewegen:
                # Dadurch endet der Test wieder in der Standposition.
                forward = self.step_length * (
                    math.sin(math.pi * phase) ** 2
                )

                target_x = self.start_x + forward
                target_z = self.start_z + lift

                upper, lower = self.inverse_kinematics(
                    target_x, target_z
                )

                # Nur das vordere linke Bein
                positions[1] = upper
                positions[2] = lower

            else:
                self.movement_active = False
                self.movement_start = None

                self.get_logger().info(
                    'Schrittbewegung abgeschlossen.'
                )

        msg = Float64MultiArray()
        msg.data = positions

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

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
