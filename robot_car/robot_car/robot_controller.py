import json
import subprocess

import rclpy
from rclpy.node import Node
from teleop_interface.msg import Teleop
from ui_interface.msg import PlayAudio, DisplayImage
import serial


class RobotController(Node):
    def __init__(self, name):
        super().__init__(name)

        self.teleop_subscription = self.create_subscription(
            Teleop,
            'teleop_robot_cmds',
            self.teleop_callback,
            10
        )

        self.voice_subscription = self.create_subscription(
            PlayAudio,
            'voice_cmds',
            self.voice_cmds_callback,
            10
        )

        self.display_subscription = self.create_subscription(
            DisplayImage,
            'display_cmds',
            self.display_callback,
            10
        )

        self.direction_to_int = {"forward": 0, "backward": 1,"left": 2, "right": 3, "stop": 4}

        self.serial_port = serial.Serial('/dev/ttyUSB0', 115200)

        self.displayed_img = None
        self.played_audio = None
        self.proc_audio = None

    def voice_cmds_callback(self, msg):

        if self.proc_audio is not None and self.proc_audio.poll() is None and \
                not self.played_audio == msg.audio_path:
            self.proc_audio.terminate()
            self.proc_audio.wait()

        if self.proc_audio is None or self.proc_audio.poll() is not None:
            if not msg.audio_path == '':
                self.proc_audio = subprocess.Popen(["mpg123", msg.audio_path])

            self.played_audio = msg.audio_path
    

    def display_callback(self, msg):
        if self.displayed_img is None or not self.displayed_img == msg.image_path:
            subprocess.Popen(["pqiv", "-f", "--hide-info-box", msg.image_path])
            self.displayed_img = msg.image_path

    def teleop_callback(self, msg):
        self.get_logger().info(f'Msg received: {msg.direction} {msg.speed} {msg.duration}')

        direction_ = int(self.direction_to_int[msg.direction])
        duration_ = int(msg.duration)
        speed_ = int(msg.speed)

        request_ = {"speed": speed_, "duration": duration_, "direction": direction_}

        print(f'{json.dumps(request_)}')

        self.serial_port.write(f'{json.dumps(request_)}\n'.encode())


def main(args=None):
    rclpy.init(args=args)
    robot_controller = RobotController('robot_controller_node')
    rclpy.spin(robot_controller)
    rclpy.shutdown()

if __name__ == "__main__":
    main()