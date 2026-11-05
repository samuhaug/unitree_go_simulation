#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64MultiArray
from trajectory_msgs.msg import JointTrajectory


JOINT_MAPPING = {
    "lf_hip_joint": "FL_hip_joint",
    "lf_upper_leg_joint": "FL_upper_leg_joint",
    "lf_lower_leg_joint": "FL_lower_leg_joint",
    "rf_hip_joint": "FR_hip_joint",
    "rf_upper_leg_joint": "FR_upper_leg_joint",
    "rf_lower_leg_joint": "FR_lower_leg_joint",
    "lh_hip_joint": "RL_hip_joint",
    "lh_upper_leg_joint": "RL_upper_leg_joint",
    "lh_lower_leg_joint": "RL_lower_leg_joint",
    "rh_hip_joint": "RR_hip_joint",
    "rh_upper_leg_joint": "RR_upper_leg_joint",
    "rh_lower_leg_joint": "RR_lower_leg_joint",
}

ORDER = [
    "FL_hip_joint", "FL_upper_leg_joint", "FL_lower_leg_joint",
    "FR_hip_joint", "FR_upper_leg_joint", "FR_lower_leg_joint",
    "RL_hip_joint", "RL_upper_leg_joint", "RL_lower_leg_joint",
    "RR_hip_joint", "RR_upper_leg_joint", "RR_lower_leg_joint",
]

START = [0.0, 0.8, -1.6] * 4

STAND_SECONDS = 8.0
RATE = 30.0
MAX_SPEED = 1.0

# Maximale Beschleunigung pro Sekunde
LINEAR_ACCEL = 0.45
ANGULAR_ACCEL = 0.80
CMD_TIMEOUT = 0.5
CHAMP_TIMEOUT = 0.5

MAX_DEVIATION = [0.15, 0.25, 0.35] * 4

DRIFT_GAIN = 0.12
DRIFT_MAX = 0.08
DRIFT_ALPHA = 0.03
DRIFT_INITIAL = -0.03

TURN_DRIFT_GAIN = 0.10
TURN_DRIFT_MAX = 0.08
TURN_DRIFT_INITIAL = -0.02

TURN_Y_GAIN = 0.05
TURN_Y_MAX = 0.05
TURN_Y_INITIAL = 0.0



class ManualAdapter(Node):

    def __init__(self):
        super().__init__("champ_manual_adapter")

        self.joint_pub = self.create_publisher(
            Float64MultiArray,
            "/leg_position_controller/commands",
            10,
        )

        self.velocity_pub = self.create_publisher(
            Twist,
            "/champ/cmd_vel",
            10,
        )

        self.create_subscription(
            Twist,
            "/cmd_vel",
            self.velocity_callback,
            10,
        )

        self.create_subscription(
            JointTrajectory,
            "/champ/joint_trajectory",
            self.joint_callback,
            10,
        )

        self.odom_x_filtered = 0.0
        self.odom_y_filtered = 0.0
        self.odom_received = False
        self.drift_correction = DRIFT_INITIAL
        self.drift_active = False
        self.turn_drift_correction = TURN_DRIFT_INITIAL
        self.turn_drift_active = False
        self.turn_y_correction = TURN_Y_INITIAL

        self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10,
        )

        self.current = START.copy()
        self.stand = None
        self.target = START.copy()

        self.phase = "WAITING"
        self.stand_started = None

        self.last_cmd = None
        self.last_champ = None
        self.requested_velocity = Twist()
        self.smoothed_velocity = Twist()

        self.timer = self.create_timer(
            1.0 / RATE,
            self.update,
        )

        self.get_logger().info(
            "Manueller CHAMP-Adapter gestartet. "
            "Warte auf Standposition."
        )

    def odom_callback(self, msg):
        measured_x = msg.twist.twist.linear.x
        measured_y = msg.twist.twist.linear.y

        if not (math.isfinite(measured_x) and math.isfinite(measured_y)):
            return

        if not self.odom_received:
            self.odom_x_filtered = measured_x
            self.odom_y_filtered = measured_y
            self.odom_received = True
        else:
            self.odom_x_filtered = (
                (1.0 - DRIFT_ALPHA) * self.odom_x_filtered
                + DRIFT_ALPHA * measured_x
            )
            self.odom_y_filtered = (
                (1.0 - DRIFT_ALPHA) * self.odom_y_filtered
                + DRIFT_ALPHA * measured_y
            )

    def velocity_callback(self, msg):
        # Erlaubte Bewegungsrichtungen begrenzen.
        velocity = Twist()

        velocity.linear.x = max(
            -0.20,
            min(0.30, msg.linear.x),
        )

        velocity.linear.y = max(
            -0.15,
            min(0.15, msg.linear.y),
        )

        velocity.angular.z = max(
            -0.40,
            min(0.40, msg.angular.z),
        )

        self.requested_velocity = velocity
        self.last_cmd = self.get_clock().now()

    def joint_callback(self, msg):
        if not msg.points:
            return

        if len(msg.joint_names) != 12:
            return

        if len(set(msg.joint_names)) != 12:
            return

        if set(msg.joint_names) != set(JOINT_MAPPING):
            return

        values = msg.points[0].positions

        if len(values) != 12:
            return

        by_name = {
            JOINT_MAPPING[name]: value
            for name, value in zip(
                msg.joint_names,
                values,
            )
        }

        ordered = [
            by_name[name]
            for name in ORDER
        ]

        if not all(math.isfinite(x) for x in ordered):
            return

        now = self.get_clock().now()

        if self.stand is None:
            for i, value in enumerate(ordered):
                allowed = [0.15, 0.30, 0.50][i % 3]

                if abs(value - START[i]) > allowed:
                    return

            self.stand = ordered
            self.stand_started = now
            self.phase = "STAND"

            self.get_logger().info(
                "Standposition empfangen. "
                "Beginne sanften Übergang."
            )

        self.last_champ = now

        if self.phase == "ACTIVE":
            self.target = [
                max(
                    self.stand[i] - MAX_DEVIATION[i],
                    min(
                        self.stand[i] + MAX_DEVIATION[i],
                        value,
                    ),
                )
                for i, value in enumerate(ordered)
            ]

    def update(self):
        now = self.get_clock().now()

        # Geschwindigkeit nur bei aktuellen Befehlen weitergeben.
        velocity = Twist()

        if self.phase == "ACTIVE" and self.last_cmd is not None:
            age = (
                now - self.last_cmd
            ).nanoseconds / 1e9

            if age <= CMD_TIMEOUT:
                velocity = self.requested_velocity

        # Adaptive Rueckwaertskorrektur nur beim Seitwaertslaufen.
        sideways = (
            abs(velocity.linear.y) > 0.01
            and abs(velocity.linear.x) < 0.06
            and abs(velocity.angular.z) < 0.01
        )

        if sideways:
            if not self.drift_active:
                self.drift_correction = DRIFT_INITIAL
                self.drift_active = True

            if self.odom_received:
                self.drift_correction -= (
                    DRIFT_GAIN * self.odom_x_filtered / RATE
                )

            self.drift_correction = max(
                -DRIFT_MAX,
                min(0.0, self.drift_correction),
            )
            velocity.linear.x = self.drift_correction
        else:
            self.drift_active = False
            self.drift_correction = DRIFT_INITIAL

        # Adaptive Vorwaertsdriftkorrektur bei reiner Drehung (A/D).
        turning = (
            abs(velocity.angular.z) > 0.01
            and abs(velocity.linear.x) < 0.06
            and abs(velocity.linear.y) < 0.01
        )

        if turning:
            if not self.turn_drift_active:
                self.turn_drift_correction = TURN_DRIFT_INITIAL
                self.turn_drift_active = True

            if self.odom_received:
                self.turn_drift_correction -= (
                    TURN_DRIFT_GAIN * self.odom_x_filtered / RATE
                )

            self.turn_drift_correction = max(
                -TURN_DRIFT_MAX,
                min(0.0, self.turn_drift_correction),
            )
            velocity.linear.x = self.turn_drift_correction

            # Seitliche Drift beim Drehen adaptiv ausgleichen.
            if self.odom_received:
                self.turn_y_correction -= (
                    TURN_Y_GAIN * self.odom_y_filtered / RATE
                )

            self.turn_y_correction = max(
                -TURN_Y_MAX,
                min(TURN_Y_MAX, self.turn_y_correction),
            )
            velocity.linear.y = self.turn_y_correction
        else:
            self.turn_drift_active = False
            self.turn_drift_correction = TURN_DRIFT_INITIAL
            self.turn_y_correction = TURN_Y_INITIAL

        # Nur beim aktiven Fahrbefehl sanft beschleunigen.
        # Bei STOP oder Timeout sofort auf null setzen.
        if (
            velocity.linear.x == 0.0
            and velocity.linear.y == 0.0
            and velocity.angular.z == 0.0
        ):
            self.smoothed_velocity = Twist()
        else:
            linear_step = LINEAR_ACCEL / RATE
            angular_step = ANGULAR_ACCEL / RATE

            linear_x_delta = (
                velocity.linear.x - self.smoothed_velocity.linear.x
            )
            linear_y_delta = (
                velocity.linear.y - self.smoothed_velocity.linear.y
            )
            angular_delta = (
                velocity.angular.z - self.smoothed_velocity.angular.z
            )

            self.smoothed_velocity.linear.x += max(
                -linear_step, min(linear_step, linear_x_delta)
            )
            self.smoothed_velocity.linear.y += max(
                -linear_step, min(linear_step, linear_y_delta)
            )
            self.smoothed_velocity.angular.z += max(
                -angular_step, min(angular_step, angular_delta)
            )
        self.velocity_pub.publish(self.smoothed_velocity)

        if self.stand is None:
            return

        if self.phase == "STAND":
            elapsed = (
                now - self.stand_started
            ).nanoseconds / 1e9

            alpha = min(
                elapsed / STAND_SECONDS,
                1.0,
            )

            alpha = alpha * alpha * (3.0 - 2.0 * alpha)

            desired = [
                a + alpha * (b - a)
                for a, b in zip(START, self.stand)
            ]

            if elapsed >= STAND_SECONDS:
                self.phase = "ACTIVE"
                self.get_logger().info(
                    "Bereit für manuelle Steuerung."
                )

        else:
            champ_fresh = (
                self.last_champ is not None
                and (
                    now - self.last_champ
                ).nanoseconds / 1e9 <= CHAMP_TIMEOUT
            )

            desired = (
                self.target
                if champ_fresh
                else self.stand
            )

        max_step = MAX_SPEED / RATE

        for i in range(12):
            delta = desired[i] - self.current[i]

            delta = max(
                -max_step,
                min(max_step, delta),
            )

            self.current[i] += delta

        message = Float64MultiArray()
        message.data = self.current.copy()
        self.joint_pub.publish(message)


def main():
    rclpy.init()
    node = ManualAdapter()

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
