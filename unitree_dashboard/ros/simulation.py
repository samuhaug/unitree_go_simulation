import os
import subprocess
import threading

_lock = threading.Lock()
_process = None


def is_running():
    global _process

    with _lock:
        if _process is not None and _process.poll() is None:
            return True

        result = subprocess.run(
            ["pgrep", "-f", r"[/]ros2 launch unitree_teleop go2_full\.launch\.py($| )"],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0


def start_simulation():
    global _process

    with _lock:
        if _process is not None and _process.poll() is None:
            return False

        result = subprocess.run(
            ["pgrep", "-f", r"[/]ros2 launch unitree_teleop go2_full\.launch\.py($| )"],
            capture_output=True,
            check=False,
        )

        if result.returncode == 0:
            return False

        _process = subprocess.Popen(
            [
                "/bin/bash",
                "-c",
                'source "${ROS_SETUP:-/opt/ros/jazzy/setup.bash}" && '
                'source "${CHAMP_SETUP:-$HOME/champ_ws/install/setup.bash}" && '
                'source "${INTEGRATION_SETUP:-$HOME/ros2_integration_ws/install/setup.bash}" && '
                "exec ros2 launch unitree_teleop go2_full.launch.py",
            ],
            start_new_session=True,
        )

        return True
