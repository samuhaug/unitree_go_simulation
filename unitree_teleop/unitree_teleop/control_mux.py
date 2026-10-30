#!/usr/bin/env python3

import math
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import String


class ControlMux(Node):

    def __init__(self):
        super().__init__("go2_control_mux")

        self.mode = "STOP"

        self.last_manual = None
        self.last_auto = None

        self.manual_command = Twist()
        self.auto_command = Twist()

        self.timeout = 0.5

        self.publisher = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        self.mode_publisher = self.create_publisher(
            String,
            "/control_mode",
            10
        )

        self.create_subscription(
            Twist,
            "/cmd_vel_manual",
            self.manual_callback,
            10
        )

        self.create_subscription(
            Twist,
            "/cmd_vel_safe",
            self.auto_callback,
            10
        )

        self.create_subscription(
            String,
            "/control_mode/set",
            self.mode_callback,
            10
        )

        self.timer = self.create_timer(
            0.05,
            self.update
        )

        self.get_logger().info(
            "Control Mux gestartet. Anfangsmodus: STOP"
        )

    def manual_callback(self, msg):
        if self.mode != "MANUAL":
            return

        if not self.valid_command(msg):
            return

        self.manual_command = self.limit_command(msg)
        self.last_manual = time.monotonic()

    def auto_callback(self, msg):
        if self.mode != "AUTO":
            return

        if not self.valid_command(msg):
            return

        self.auto_command = self.limit_command(msg)
        self.last_auto = time.monotonic()

    def mode_callback(self, msg):
        new_mode = msg.data.strip().upper()

        if new_mode not in ("MANUAL", "AUTO", "STOP"):
            self.get_logger().warn(
                f"Ungültiger Modus: {new_mode}"
            )
            return

        if new_mode != self.mode:
            self.mode = new_mode

            # Alte Bewegungsbefehle verwerfen.
            self.last_manual = None
            self.last_auto = None

            # Beim Umschalten sofort stoppen.
            self.publisher.publish(Twist())

            self.get_logger().info(
                f"Steuerungsmodus: {self.mode}"
            )

    def valid_command(self, msg):
        values = [
            msg.linear.x,
            msg.linear.y,
            msg.linear.z,
            msg.angular.x,
            msg.angular.y,
            msg.angular.z,
        ]

        return all(math.isfinite(value) for value in values)

    def limit_command(self, msg):
        command = Twist()

        command.linear.x = max(
            -0.15,
            min(0.20, msg.linear.x)
        )

        command.angular.z = max(
            -0.30,
            min(0.30, msg.angular.z)
        )

        return command

    def update(self):
        now = time.monotonic()

        command = Twist()

        if self.mode == "MANUAL":
            if (
                self.last_manual is not None
                and now - self.last_manual <= self.timeout
            ):
                command = self.manual_command

        elif self.mode == "AUTO":
            if (
                self.last_auto is not None
                and now - self.last_auto <= self.timeout
            ):
                command = self.auto_command

        self.publisher.publish(command)

        mode_message = String()
        mode_message.data = self.mode

        self.mode_publisher.publish(mode_message)


def main():
    rclpy.init()

    node = ControlMux()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

