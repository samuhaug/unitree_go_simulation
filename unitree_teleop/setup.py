from setuptools import find_packages, setup
from glob import glob

package_name = 'unitree_teleop'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='samuel',
    maintainer_email='samuel@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'go2_controller = unitree_teleop.go2_controller:main',
            'champ_manual_adapter = unitree_teleop.champ_manual_adapter:main',
            'wasd_teleop = unitree_teleop.wasd_teleop:main',
        ],
    },
)
