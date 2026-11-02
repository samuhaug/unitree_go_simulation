import os
import psutil
import signal
import subprocess
import threading
import time

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






def stop_simulation():
    """Beendet die vom Dashboard gestartete Simulationssitzung."""
    global _process

    with _lock:
        process = _process

        if process is None:
            return False, "Keine vom Dashboard gestartete Simulation bekannt"

        # start_new_session=True erzeugt eine eigene Sitzung.
        session_id = process.pid

        def members():
            """Aktive Prozesse dieser Sitzung ermitteln."""
            result = []

            for proc in psutil.process_iter(["pid", "status"]):
                try:
                    if (
                        os.getsid(proc.pid) == session_id
                        and proc.status() != psutil.STATUS_ZOMBIE
                    ):
                        result.append(proc)
                except (ProcessLookupError, psutil.NoSuchProcess,
                        psutil.AccessDenied, PermissionError):
                    continue

            return result

        def send_signal(sig):
            for proc in members():
                try:
                    proc.send_signal(sig)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        for sig, timeout in (
            (signal.SIGINT, 12),
            (signal.SIGTERM, 5),
            (signal.SIGKILL, 3),
        ):
            send_signal(sig)

            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                process.poll()

                if not members():
                    _process = None
                    return True, "Simulation vollständig beendet"

                time.sleep(0.2)

        process.poll()

        if members():
            return False, "Einige Simulationsprozesse laufen noch"

        _process = None
        return True, "Simulation vollständig beendet"
