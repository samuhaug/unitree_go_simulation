import threading

import cv2
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import qos_profile_sensor_data


class DashboardCamera(Node):
    def __init__(self):
        super().__init__("dashboard_camera")

        self._lock = threading.Lock()
        self._latest_jpeg = None

        self.create_subscription(
            Image,
            "/dashboard/camera/image",
            self._image_callback,
            qos_profile_sensor_data
        )

        self.get_logger().info("Dashboard-Kamera bereit")

    def _image_callback(self, msg):
        try:
            if msg.encoding == "rgb8":
                channels = 3
                conversion = cv2.COLOR_RGB2BGR
            elif msg.encoding == "bgr8":
                channels = 3
                conversion = None
            elif msg.encoding == "rgba8":
                channels = 4
                conversion = cv2.COLOR_RGBA2BGR
            elif msg.encoding == "bgra8":
                channels = 4
                conversion = cv2.COLOR_BGRA2BGR
            else:
                return

            row_bytes = msg.width * channels

            if msg.step < row_bytes:
                return

            image = np.frombuffer(
                msg.data, dtype=np.uint8
            ).reshape(msg.height, msg.step)

            image = image[:, :row_bytes].reshape(
                msg.height, msg.width, channels
            )

            if conversion is not None:
                image = cv2.cvtColor(image, conversion)

            success, jpeg = cv2.imencode(
                ".jpg",
                image,
                [cv2.IMWRITE_JPEG_QUALITY, 80]
            )

            if success:
                with self._lock:
                    self._latest_jpeg = jpeg.tobytes()

        except (ValueError, cv2.error) as error:
            self.get_logger().warning(
                f"Kamerabild konnte nicht verarbeitet werden: {error}"
            )

    def get_jpeg(self):
        with self._lock:
            return self._latest_jpeg
