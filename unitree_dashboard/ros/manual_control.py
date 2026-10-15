import time
import threading

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class ManualControl(Node):
    def __init__(self):
        super().__init__("go2_dashboard_control")

        self.publisher = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        self.lock = threading.Lock()
        self.linear = 0.0
        self.angular = 0.0
        self.last_command = 0.0

        self.timer = self.create_timer(
            0.05,
            self.publish_command
        )

    def set_command(self, linear, angular):
        with self.lock:
            self.linear = max(-0.15, min(0.20, float(linear)))
            self.angular = max(-0.30, min(0.30, float(angular)))
            self.last_command = time.monotonic()

    def stop(self):
        self.set_command(0.0, 0.0)

    def publish_command(self):
        with self.lock:
            if time.monotonic() - self.last_command > 0.35:
                linear = 0.0
                angular = 0.0
            else:
                linear = self.linear
                angular = self.angular

        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular

        self.publisher.publish(msg)
