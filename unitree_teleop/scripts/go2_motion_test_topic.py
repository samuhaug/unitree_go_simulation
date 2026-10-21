#!/usr/bin/env python3
import math
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

JOINTS = [
    "FL_hip_joint", "FL_upper_leg_joint", "FL_lower_leg_joint",
    "FR_hip_joint", "FR_upper_leg_joint", "FR_lower_leg_joint",
    "RL_hip_joint", "RL_upper_leg_joint", "RL_lower_leg_joint",
    "RR_hip_joint", "RR_upper_leg_joint", "RR_lower_leg_joint",
]

L1 = 0.213
L2 = 0.213

STRIDE = 0.07
LIFT = 0.025
CYCLE = 1.6
STANCE_FRACTION = 0.60
CYCLES = 5
DT = 0.05

STAND = [0.0, 0.8, -1.6] * 4
OFFSETS = (0.0, 0.5, 0.5, 0.0)


def inverse_kinematics(x, z):
    d2 = x * x + z * z
    cos_q2 = (d2 - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    cos_q2 = max(-1.0, min(1.0, cos_q2))
    q2 = -math.acos(cos_q2)

    q1 = math.atan2(x, z) - math.atan2(
        L2 * math.sin(q2),
        L1 + L2 * math.cos(q2)
    )
    return q1, q2


def foot_target(phase):
    phase %= 1.0
    half = STRIDE / 2.0
    z_down = 0.296

    if phase < STANCE_FRACTION:
        u = phase / STANCE_FRACTION
        x = -half + STRIDE * u
        z = z_down
    else:
        u = (phase - STANCE_FRACTION) / (1.0 - STANCE_FRACTION)
        x = half - STRIDE * u
        z = z_down - LIFT * math.sin(math.pi * u)

    return x, z


def make_pose(cycle_phase):
    q = STAND.copy()

    for leg, offset in enumerate(OFFSETS):
        phase = (cycle_phase + offset) % 1.0
        x, z = foot_target(phase)
        q1, q2 = inverse_kinematics(x, z)
        q[3 * leg + 1] = q1
        q[3 * leg + 2] = q2

    return q


class MotionTest(Node):
    def __init__(self):
        super().__init__("go2_motion_test_topic")
        self.publisher = self.create_publisher(
            Float64MultiArray,
            "/leg_position_controller/commands",
            10,
        )

    def send(self, positions):
        msg = Float64MultiArray()
        msg.data = positions
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = MotionTest()

    try:
        # Controller erhält zuerst die bekannte Standpose.
        node.send(STAND)
        time.sleep(1.0)

        node.get_logger().info("Bewegungstest startet: 5 Zyklen.")
        start = time.monotonic()
        total = CYCLE * CYCLES

        while time.monotonic() - start < total:
            t = time.monotonic() - start
            node.send(make_pose(t / CYCLE))
            time.sleep(DT)

        # Zum Abschluss Standpose senden und halten.
        node.send(STAND)
        for _ in range(20):
            rclpy.spin_once(node, timeout_sec=0.0)
            node.send(STAND)
            time.sleep(DT)

        node.get_logger().info("Bewegungstest beendet.")

    except KeyboardInterrupt:
        node.get_logger().warn("Abbruch! Standpose wird gesendet.")
        for _ in range(20):
            node.send(STAND)
            time.sleep(DT)

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
