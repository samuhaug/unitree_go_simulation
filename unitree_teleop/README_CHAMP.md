# Unitree Go2 – CHAMP-WASD-Steuerung

## Voraussetzungen

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- CHAMP-Workspace: ~/champ_ws
- ROS-2-Workspace: ~/ros2_ws

CHAMP-Referenz:
https://github.com/khaledgabr77/unitree_go2_ros2

Benötigte ROS-2-Pakete:
champ, champ_base, champ_msgs,
unitree_go2_description, unitree_go2_sim

## Simulation starten

Vier Terminals verwenden.

### Terminal 1 – Gazebo

source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch unitree_description simulation.launch.py

### Terminal 2 – CHAMP

source /opt/ros/jazzy/setup.bash
source ~/champ_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch unitree_teleop champ.launch.py

### Terminal 3 – Adapter

source /opt/ros/jazzy/setup.bash
source ~/champ_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run unitree_teleop champ_manual_adapter

### Terminal 4 – WASD

source /opt/ros/jazzy/setup.bash
source ~/champ_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run unitree_teleop wasd_teleop

## Steuerung

W: Vorwärts (0,05 m/s)
S: Rückwärts (0,10 m/s)
A: Links drehen
D: Rechts drehen
Leertaste: Stoppen
Q: Beenden

## Hinweise

Den bisherigen go2_controller nicht gleichzeitig starten.

CHAMP-Referenzpfad standardmäßig:
~/go2_references/unitree_go2_ros2

Alternativer Pfad:
export UNITREE_GO2_CHAMP_ROOT="/pfad/zum/unitree_go2_ros2"

## Vereinfachter Start (empfohlen)

Nach dem Einbinden der ROS-2-Workspaces sind nur zwei Terminals nötig.

### Terminal 1 – Gesamte Simulation

source /opt/ros/jazzy/setup.bash
source ~/champ_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch unitree_teleop go2_wasd.launch.py

Dieser Befehl startet Gazebo, CHAMP und den Adapter.

### Terminal 2 – WASD-Steuerung

source /opt/ros/jazzy/setup.bash
source ~/champ_ws/install/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 run unitree_teleop wasd_teleop

Die Tastatureingaben erfolgen im zweiten Terminal.

## CHAMP auf einem neuen Rechner einrichten

mkdir -p ~/go2_references
git clone https://github.com/khaledgabr77/unitree_go2_ros2.git \
  ~/go2_references/unitree_go2_ros2

mkdir -p ~/champ_ws/src

for paket in champ champ_base champ_msgs unitree_go2_description unitree_go2_sim; do
    ln -s ~/go2_references/unitree_go2_ros2/$paket ~/champ_ws/src/$paket
done

source /opt/ros/jazzy/setup.bash
cd ~/champ_ws
colcon build --symlink-install

Hinweis: Zusätzlich müssen die Systemabhängigkeiten der Pakete
installiert sein. Der erfolgreiche Build wurde bisher auf Ubuntu 24.04
mit ROS 2 Jazzy getestet.
