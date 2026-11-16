import argparse
import re
import subprocess
import sys


WORLD_NAME = 'go2_world'
ENTITY_NAME = 'nav_demo_barrier'
POSE_TOPIC = f'/world/{WORLD_NAME}/pose/info'
ENTITY_PATTERN = re.compile(
    rf'^{re.escape(ENTITY_NAME)}(?:_\d+)?$'
)

DEFAULT_X = -0.221859
DEFAULT_Y = 0.838271
DEFAULT_LENGTH = 1.890253
DEFAULT_WIDTH = 0.300000
DEFAULT_HEIGHT = 0.600000
DEFAULT_YAW = 0.0

COSTMAP_SERVICES = [
    '/global_costmap/clear_entirely_global_costmap',
    '/local_costmap/clear_entirely_local_costmap',
]


def run_command(command):
    print()
    print('Ausgeführt:')
    print(' '.join(command))
    print()

    return subprocess.run(
        command,
        check=False,
    ).returncode


def find_obstacle_entities():
    try:
        result = subprocess.run(
            [
                'timeout',
                '3',
                'gz',
                'topic',
                '-e',
                '-t',
                POSE_TOPIC,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            'Das Gazebo-Programm gz wurde nicht gefunden.'
        ) from error

    if not result.stdout.strip():
        raise RuntimeError(
            'Keine Gazebo-Poseinformationen empfangen. '
            'Die Simulation läuft möglicherweise nicht.'
        )

    names = re.findall(
        r'^\s*name:\s*"([^"]+)"\s*$',
        result.stdout,
        re.MULTILINE,
    )

    return sorted({
        name
        for name in names
        if ENTITY_PATTERN.fullmatch(name)
    })


def build_sdf(length, width, height):
    return f"""<sdf version='1.9'>
  <model name='{ENTITY_NAME}'>
    <static>true</static>
    <link name='barrier_link'>
      <collision name='barrier_collision'>
        <geometry>
          <box>
            <size>{length:.6f} {width:.6f} {height:.6f}</size>
          </box>
        </geometry>
      </collision>
      <visual name='barrier_visual'>
        <cast_shadows>true</cast_shadows>
        <geometry>
          <box>
            <size>{length:.6f} {width:.6f} {height:.6f}</size>
          </box>
        </geometry>
        <material>
          <ambient>0.8 0.05 0.05 1.0</ambient>
          <diffuse>0.9 0.05 0.05 1.0</diffuse>
          <specular>0.2 0.2 0.2 1.0</specular>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""


def validate_dimensions(length, width, height):
    values = {
        'length': length,
        'width': width,
        'height': height,
    }

    for name, value in values.items():
        if value <= 0.0:
            raise ValueError(
                f'{name} muss größer als 0 sein, erhalten: {value}'
            )


def spawn_obstacle(args):
    try:
        validate_dimensions(
            args.length,
            args.width,
            args.height,
        )
    except ValueError as error:
        print(f'FEHLER: {error}', file=sys.stderr)
        return 2

    try:
        existing_entities = find_obstacle_entities()
    except RuntimeError as error:
        print(f'FEHLER: {error}', file=sys.stderr)
        return 3

    if existing_entities:
        print(
            'FEHLER: Mindestens ein Testblock existiert bereits:',
            file=sys.stderr,
        )

        for entity_name in existing_entities:
            print(f'  - {entity_name}', file=sys.stderr)

        print(
            'Bitte zuerst test_obstacle clear ausführen.',
            file=sys.stderr,
        )
        return 3

    sdf = build_sdf(
        args.length,
        args.width,
        args.height,
    )

    z = args.height / 2.0

    command = [
        'ros2',
        'run',
        'ros_gz_sim',
        'create',
        '-world',
        WORLD_NAME,
        '-string',
        sdf,
        '-name',
        ENTITY_NAME,
        '-allow_renaming',
        'false',
        '-x',
        f'{args.x:.6f}',
        '-y',
        f'{args.y:.6f}',
        '-z',
        f'{z:.6f}',
        '-Y',
        f'{args.yaw:.6f}',
    ]

    result = run_command(command)

    if result != 0:
        print(
            'FEHLER: Der Block konnte nicht erzeugt werden. '
            'Möglicherweise existiert er bereits.',
            file=sys.stderr,
        )
        return result

    print('Block erfolgreich erzeugt:')
    print(f'  Name:      {ENTITY_NAME}')
    print(f'  Welt:      {WORLD_NAME}')
    print(f'  Position:  x={args.x:.6f}, y={args.y:.6f}, z={z:.6f}')
    print(f'  Rotation:  yaw={args.yaw:.6f} rad')
    print(
        '  Abmessung: '
        f'{args.length:.6f} x {args.width:.6f} x {args.height:.6f} m'
    )

    return 0


def clear_costmaps():
    service_result = subprocess.run(
        ['ros2', 'service', 'list'],
        check=False,
        capture_output=True,
        text=True,
    )

    if service_result.returncode != 0:
        print(
            'WARNUNG: Costmap-Services konnten nicht abgefragt werden.',
            file=sys.stderr,
        )
        return

    available_services = set(
        service_result.stdout.splitlines()
    )

    for service in COSTMAP_SERVICES:
        if service not in available_services:
            print(
                f'WARNUNG: Service nicht verfügbar: {service}',
                file=sys.stderr,
            )
            continue

        result = run_command([
            'ros2',
            'service',
            'call',
            service,
            'nav2_msgs/srv/ClearEntireCostmap',
            '{}',
        ])

        if result != 0:
            print(
                f'WARNUNG: Costmap konnte nicht geleert werden: {service}',
                file=sys.stderr,
            )


def remove_entity(entity_name):
    command = [
        'ros2',
        'run',
        'ros_gz_sim',
        'remove',
        '--ros-args',
        '-p',
        f'world:={WORLD_NAME}',
        '-p',
        f'entity_name:={entity_name}',
    ]

    return run_command(command)


def clear_obstacle(args):
    try:
        existing_entities = find_obstacle_entities()
    except RuntimeError as error:
        print(f'FEHLER: {error}', file=sys.stderr)
        return 3

    failed_entities = []

    if not existing_entities:
        print('Kein Gazebo-Testblock vorhanden.')
    else:
        for entity_name in existing_entities:
            result = remove_entity(entity_name)

            if result == 0:
                print(
                    f'Block erfolgreich entfernt: {entity_name}'
                )
            else:
                failed_entities.append(entity_name)

    if failed_entities:
        print(
            'FEHLER: Nicht alle Testblöcke konnten entfernt werden:',
            file=sys.stderr,
        )

        for entity_name in failed_entities:
            print(f'  - {entity_name}', file=sys.stderr)

        print(
            'Die Costmaps werden deshalb nicht geleert.',
            file=sys.stderr,
        )
        return 4

    if not args.no_costmap_clear:
        clear_costmaps()

    return 0


def create_parser():
    parser = argparse.ArgumentParser(
        description=(
            'Erzeugt oder entfernt das getestete '
            'Gazebo-Navigationshindernis.'
        )
    )

    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
    )

    spawn_parser = subparsers.add_parser(
        'spawn',
        help='Erzeugt den Testblock.',
    )
    spawn_parser.add_argument(
        '--x',
        type=float,
        default=DEFAULT_X,
    )
    spawn_parser.add_argument(
        '--y',
        type=float,
        default=DEFAULT_Y,
    )
    spawn_parser.add_argument(
        '--length',
        type=float,
        default=DEFAULT_LENGTH,
    )
    spawn_parser.add_argument(
        '--width',
        type=float,
        default=DEFAULT_WIDTH,
    )
    spawn_parser.add_argument(
        '--height',
        type=float,
        default=DEFAULT_HEIGHT,
    )
    spawn_parser.add_argument(
        '--yaw',
        type=float,
        default=DEFAULT_YAW,
        help='Rotation um die Z-Achse in Radiant.',
    )
    spawn_parser.set_defaults(handler=spawn_obstacle)

    clear_parser = subparsers.add_parser(
        'clear',
        help='Entfernt den Testblock.',
    )
    clear_parser.add_argument(
        '--no-costmap-clear',
        action='store_true',
        help='Entfernt nur das Gazebo-Modell.',
    )
    clear_parser.set_defaults(handler=clear_obstacle)

    return parser


def main(args=None):
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    return parsed_args.handler(parsed_args)


if __name__ == '__main__':
    raise SystemExit(main())
