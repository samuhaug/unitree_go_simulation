#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory

JOINTS = [
    "FL_hip_joint", "FL_upper_leg_joint", "FL_lower_leg_joint",
    "FR_hip_joint", "FR_upper_leg_joint", "FR_lower_leg_joint",
    "RL_hip_joint", "RL_upper_leg_joint", "RL_lower_leg_joint",
    "RR_hip_joint", "RR_upper_leg_joint", "RR_lower_leg_joint",
]

L1 = 0.213
L2 = 0.213

# Konservative Startwerte
STRIDE = 0.07
LIFT = 0.025
CYCLE = 1.6
STANCE_FRACTION = 0.60
CYCLES = 5
DT = 0.05

# Bekannte, bisher funktionierende Standposition
STAND = [0.0, 0.8, -1.6] * 4

# FL/RR und FR/RL laufen diagonal versetzt.
OFFSETS = (0.0, 0.5, 0.5, 0.0)


def inverse_kinematics(x, z):
    """2D-Bein-IK. z ist relativ zum Hüftgelenk nach unten positiv."""
    d2 = x * x + z * z
    cos_q2 = (d2 - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    cos_q2 = max(-1.0, min(1.0, cos_q2))

    # Knie-/Unterschenkelwinkel passend zur bisherigen Standpose
    q2 = -math.acos(cos_q2)

    q1 = math.atan2(x, z) - math.atan2(
        L2 * math.sin(q2),
        L1 + L2 * math.cos(q2)
    )
    return q1, q2


def foot_target(phase):
    """Geschlossene Fußbahn: Standphase rückwärts, Schwungphase vorwärts."""
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


class Go2MotionTest(Node):
    def __init__(self):
        super().__init__("go2_foot_trajectory")
        self.client = ActionClient(
            self,
            FollowJointTrajectory,
            "/joint_trajectory_controller/follow_joint_trajectory",
        )

    def run(self):
        self.get_logger().info("Warte auf Trajectory-Controller ...")
        if not self.client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("Controller nicht erreichbar.")
            return

        traj = JointTrajectory()
        traj.joint_names = JOINTS

        point = JointTrajectoryPoint()
        point.positions = STAND
        point.time_from_start = Duration(sec=0, nanosec=0)
        traj.points.append(point)

        total = CYCLE * CYCLES
        count = int(total / DT)

        for i in range(1, count + 1):
            t = i * DT
            point = JointTrajectoryPoint()
            point.positions = make_pose(t / CYCLE)
            sec = int(t)
            point.time_from_start = Duration(
                sec=sec,
                nanosec=int((t - sec) * 1_000_000_000),
            )
            traj.points.append(point)

        point = JointTrajectoryPoint()
        point.positions = STAND
        point.time_from_start = Duration(
            sec=int(total + 0.5),
            nanosec=int(((total + 0.5) % 1) * 1_000_000_000),
        )
        traj.points.append(point)

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj

        self.get_logger().info(
            "Sende Fußtrajektorie: %d Zyklen, Schrittweite %.0f mm."
            % (CYCLES, STRIDE * 1000)
        )
        future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()

        if handle is None or not handle.accepted:
            self.get_logger().error("Trajektorie abgelehnt.")
            return

        result = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result)

        response = result.result()
        if response is not None:
            self.get_logger().info(
                "Trajektorie beendet. Controller-Status: %s"
                % response.result.error_string
            )


def main():
    rclpy.init()
    node = Go2MotionTest()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
