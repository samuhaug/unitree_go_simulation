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

        # Standposition: 4 Beine mit jeweils 3 Gelenken
        self.stand_position = [
            0.0, 0.8, -1.6,    # FL
            0.0, 0.8, -1.6,    # FR
            0.0, 0.8, -1.6,    # RL
            0.0, 0.8, -1.6     # RR
        ]

        self.movement_active = False
        self.movement_start = None

        # Kleine Testbewegung: 0.05 rad
        self.amplitude = 0.05

        # Eine Bewegung dauert 2 Sekunden
        self.movement_duration = 2.0

        # Controller mit 10 Hz aktualisieren
        self.timer = self.create_timer(
            0.1,
            self.update_controller
        )

        self.get_logger().info(
            'Go2 Controller gestartet. Warte auf /cmd_vel.'
        )

    def cmd_vel_callback(self, msg):

        # Vorwärtsbefehl startet die Testbewegung
        if msg.linear.x > 0.01:

            if not self.movement_active:
                self.movement_active = True
                self.movement_start = time.monotonic()

                self.get_logger().info(
                    'Testbewegung gestartet.'
                )

        else:
            # Stoppbefehl beendet die Bewegung
            if self.movement_active:
                self.get_logger().info(
                    'Bewegung gestoppt.'
                )

            self.movement_active = False
            self.movement_start = None

    def update_controller(self):

        positions = self.stand_position.copy()

        if self.movement_active:

            elapsed = time.monotonic() - self.movement_start

            if elapsed < self.movement_duration:

                # Eine sanfte Bewegung von 0.8 auf 0.75
                # und wieder zurück auf 0.8 rad
                phase = elapsed / self.movement_duration

                offset = self.amplitude * (
                    math.sin(math.pi * phase) ** 2
                )

                # Nur vorderes linkes Oberschenkelgelenk
                positions[1] = 0.8 + offset
                positions[2] = -1.6 - 2.0 * offset

            else:
                # Bewegung nach 2 Sekunden beenden
                self.movement_active = False
                self.movement_start = None

                self.get_logger().info(
                    'Testbewegung abgeschlossen.'
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
