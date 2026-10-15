#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
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
RATE = 20.0
MAX_SPEED = 1.0
CMD_TIMEOUT = 0.5
CHAMP_TIMEOUT = 0.5

MAX_DEVIATION = [0.15, 0.25, 0.35] * 4


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

        self.current = START.copy()
        self.stand = None
        self.target = START.copy()

        self.phase = "WAITING"
        self.stand_started = None

        self.last_cmd = None
        self.last_champ = None
        self.requested_velocity = Twist()

        self.timer = self.create_timer(
            1.0 / RATE,
            self.update,
        )

        self.get_logger().info(
            "Manueller CHAMP-Adapter gestartet. "
            "Warte auf Standposition."
        )

    def velocity_callback(self, msg):
        # Nur die benötigten Bewegungsrichtungen erlauben.
        velocity = Twist()

        velocity.linear.x = max(
            -0.10,
            min(0.10, msg.linear.x),
        )

        velocity.angular.z = max(
            -0.2,
            min(0.2, msg.angular.z),
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

        self.velocity_pub.publish(velocity)

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
