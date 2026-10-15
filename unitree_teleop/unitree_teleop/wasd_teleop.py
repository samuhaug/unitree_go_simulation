#!/usr/bin/env python3

import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist


LINEAR_SPEED = 0.05
BACKWARD_SPEED = 0.10
ANGULAR_SPEED = 0.20
COMMAND_DURATION = 0.25
PUBLISH_INTERVAL = 0.05


def publish_velocity(publisher, linear=0.0, angular=0.0):
    msg = Twist()
    msg.linear.x = linear
    msg.angular.z = angular
    publisher.publish(msg)


def main():
    rclpy.init()
    node = rclpy.create_node("wasd_teleop")
    publisher = node.create_publisher(Twist, "/cmd_vel", 10)

    old_settings = termios.tcgetattr(sys.stdin)

    print()
    print("===================================")
    print("      GO2 WASD-STEUERUNG")
    print("===================================")
    print("W = Vorwärts")
    print("S = Rückwärts")
    print("A = Links drehen")
    print("D = Rechts drehen")
    print("LEERTASTE = Stopp")
    print("Q = Beenden")
    print()
    print("Taste drücken und halten.")
    print("Nach Loslassen stoppt der Roboter.")
    print("===================================")

    linear = 0.0
    angular = 0.0
    last_key_time = 0.0

    try:
        tty.setcbreak(sys.stdin.fileno())

        while rclpy.ok():
            readable, _, _ = select.select(
                [sys.stdin], [], [], PUBLISH_INTERVAL
            )

            if readable:
                key = sys.stdin.read(1).lower()

                if key == "q":
                    break

                if key == "w":
                    linear = LINEAR_SPEED
                    angular = 0.0
                    last_key_time = time.monotonic()

                elif key == "s":
                    linear = -BACKWARD_SPEED
                    angular = 0.0
                    last_key_time = time.monotonic()

                elif key == "a":
                    linear = 0.0
                    angular = ANGULAR_SPEED
                    last_key_time = time.monotonic()

                elif key == "d":
                    linear = 0.0
                    angular = -ANGULAR_SPEED
                    last_key_time = time.monotonic()

                elif key == " ":
                    linear = 0.0
                    angular = 0.0
                    last_key_time = 0.0

            if time.monotonic() - last_key_time > COMMAND_DURATION:
                linear = 0.0
                angular = 0.0

            publish_velocity(publisher, linear, angular)

    except KeyboardInterrupt:
        pass

    finally:
        publish_velocity(publisher)
        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            old_settings,
        )
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

        print("\nWASD-Steuerung beendet.")


if __name__ == "__main__":
    main()
