import time
import threading

from geometry_msgs.msg import Twist
from std_msgs.msg import String
from rclpy.node import Node


class ManualControl(Node):
    def __init__(self):
        super().__init__("go2_dashboard_control")

        self.lock = threading.Lock()

        self.linear = 0.0
        self.angular = 0.0
        self.last_command = 0.0

        self.current_mode = "UNKNOWN"
        self.last_mode_update = 0.0

        self.publisher = self.create_publisher(
            Twist,
            "/cmd_vel_manual",
            10
        )

        self.mode_publisher = self.create_publisher(
            String,
            "/control_mode/set",
            10
        )

        self.create_subscription(
            String,
            "/control_mode",
            self.mode_callback,
            10
        )

        self.timer = self.create_timer(
            0.05,
            self.publish_command
        )

    def mode_callback(self, msg):
        with self.lock:
            self.current_mode = msg.data
            self.last_mode_update = time.monotonic()

    def get_mode(self):
        with self.lock:
            if time.monotonic() - self.last_mode_update > 1.0:
                return "UNKNOWN"

            return self.current_mode

    def set_mode(self, mode):
        mode = mode.upper()

        if mode not in ("MANUAL", "AUTO", "STOP"):
            return False

        self.stop()

        message = String()
        message.data = mode
        self.mode_publisher.publish(message)

        return True

    def set_command(self, linear, angular):
        with self.lock:
            if (
                self.current_mode != "MANUAL"
                or time.monotonic() - self.last_mode_update > 1.0
            ):
                self.linear = 0.0
                self.angular = 0.0
                return False

            self.linear = max(-0.15, min(0.20, float(linear)))
            self.angular = max(-0.30, min(0.30, float(angular)))
            self.last_command = time.monotonic()

            return True

    def stop(self):
        with self.lock:
            self.linear = 0.0
            self.angular = 0.0
            self.last_command = 0.0

    def publish_command(self):
        with self.lock:
            mode_valid = (
                self.current_mode == "MANUAL"
                and time.monotonic() - self.last_mode_update <= 1.0
            )

            command_valid = (
                time.monotonic() - self.last_command <= 0.35
            )

            if mode_valid and command_valid:
                linear = self.linear
                angular = self.angular
            else:
                linear = 0.0
                angular = 0.0

        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular

        self.publisher.publish(msg)
