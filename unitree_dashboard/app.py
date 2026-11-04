import os
import sys
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from flask import Flask, Response, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(__file__))

from ros.camera import DashboardCamera
from ros.manual_control import ManualControl
from ros.navigation import cancel_navigation, navigation_available
from ros.simulation import is_running, start_simulation, stop_simulation


app = Flask(__name__)

rclpy.init()
controller = ManualControl()

# Gemeinsamer ROS2-Executor für Steuerung und Kamera
camera = DashboardCamera()

executor = MultiThreadedExecutor(num_threads=2)
executor.add_node(controller)
executor.add_node(camera)

ros_thread = threading.Thread(
    target=executor.spin,
    daemon=True
)
ros_thread.start()


@app.route("/")
def index():
    return render_template("index.html")



@app.route("/api/camera/stream")
def camera_stream():
    def generate():
        while True:
            jpeg = camera.get_jpeg()

            if jpeg is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(jpeg)}\r\n".encode()
                    + b"\r\n"
                    + jpeg
                    + b"\r\n"
                )

            time.sleep(1 / 30)

    return Response(
        generate(),
        content_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"}
    )


@app.route("/api/status")
def status():
    mode = controller.get_mode()

    return jsonify({
        "connected": mode != "UNKNOWN",
        "mode": mode,
        "navigation_available": navigation_available(controller)
    })
@app.route("/api/mode", methods=["POST"])
def set_mode():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")

    if not isinstance(mode, str):
        return jsonify({"error": "Ungueltiger Modus"}), 400

    mode = mode.strip().upper()

    if mode not in ("MANUAL", "AUTO", "STOP"):
        return jsonify({"error": "Ungueltiger Modus"}), 400

    if controller.get_mode() == "UNKNOWN":
        return jsonify({"error": "Control Mux nicht erreichbar"}), 503

    controller.set_mode(mode)

    return jsonify({
        "success": True,
        "requested_mode": mode
    })
@app.route("/api/control", methods=["POST"])
def control():
    data = request.get_json(silent=True) or {}

    try:
        linear = float(data.get("linear", 0.0))
        angular = float(data.get("angular", 0.0))
    except (TypeError, ValueError):
        return jsonify({"error": "Ungueltige Geschwindigkeit"}), 400

    if not (-0.20 <= linear <= 0.30):
        return jsonify({"error": "Lineargeschwindigkeit ausserhalb des Bereichs"}), 400

    if not (-0.40 <= angular <= 0.40):
        return jsonify({"error": "Drehgeschwindigkeit ausserhalb des Bereichs"}), 400

    if not controller.set_command(linear, angular):
        return jsonify({
            "error": "Manuelle Steuerung nicht aktiv"
        }), 409

    return jsonify({
        "success": True,
        "linear": linear,
        "angular": angular
    })


@app.route("/api/stop", methods=["POST"])
def stop():
    controller.stop()
    return jsonify({"success": True})


@app.route("/api/emergency_stop", methods=["POST"])
def emergency_stop():
    controller.stop()
    controller.set_mode("STOP")

    cancel_requested = cancel_navigation(controller)

    return jsonify({
        "success": True,
        "requested_mode": "STOP",
        "navigation_cancel_requested": cancel_requested
    })


@app.route("/api/simulation", methods=["GET"])
def simulation_status():
    return jsonify({"running": is_running()})


@app.route("/api/simulation/start", methods=["POST"])
def simulation_start():
    if is_running():
        return jsonify({
            "success": False,
            "message": "Simulation läuft bereits"
        }), 409

    if not start_simulation():
        return jsonify({
            "success": False,
            "message": "Simulation konnte nicht gestartet werden"
        }), 409

    return jsonify({
        "success": True,
        "message": "Gazebo, Nav2 und RViz2 werden gestartet"
    })


@app.route("/api/simulation/stop", methods=["POST"])
def simulation_stop():
    # Zuerst Roboterbewegung und Navigation stoppen.
    controller.stop()
    controller.set_mode("STOP")
    cancel_navigation(controller)

    success, message = stop_simulation()

    return jsonify({
        "success": success,
        "message": message,
        "running": is_running()
    }), 200 if success else 409


app.config['TEMPLATES_AUTO_RELOAD'] = True

if __name__ == "__main__":
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False
        )
    finally:
        controller.stop()
        executor.shutdown()
        ros_thread.join(timeout=2)
        camera.destroy_node()
        controller.destroy_node()
        rclpy.shutdown()
