import os
import sys
import threading

import rclpy
from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(__file__))

from ros.manual_control import ManualControl


app = Flask(__name__)

rclpy.init()
controller = ManualControl()

ros_thread = threading.Thread(
    target=rclpy.spin,
    args=(controller,),
    daemon=True
)
ros_thread.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    mode = controller.get_mode()

    return jsonify({
        "connected": mode != "UNKNOWN",
        "mode": mode
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

    if not (-0.15 <= linear <= 0.20):
        return jsonify({"error": "Lineargeschwindigkeit ausserhalb des Bereichs"}), 400

    if not (-0.30 <= angular <= 0.30):
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
        controller.destroy_node()
        rclpy.shutdown()
