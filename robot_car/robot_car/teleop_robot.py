import tty
import termios
import select
import sys

import rclpy
from rclpy.node import Node
from teleop_interface.msg import Teleop


def get_key(settings, timeout=0.1):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


class TeleopRobot(Node):
    def __init__(self, name):
        super().__init__(name)

        self.publisher = self.create_publisher(Teleop, 'teleop_robot_cmds', 10)

        self.direction = "stop"
        self.duration = 100
        self.speed = 255
        
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        msg = Teleop()
        msg.direction = self.direction
        msg.duration = self.duration
        msg.speed = self.speed
        self.publisher.publish(msg)


def main(args=None):

    settings = termios.tcgetattr(sys.stdin)

    rclpy.init(args=args)
    teleop_robot = TeleopRobot('teleop_robot_node')

    print("Use 'w', 'a', 's', 'd' to control the robot.")
    print("Press 'q' to exit.")

    press_key = True

    while True:

        if press_key:
            rclpy.spin_once(teleop_robot)

        char = get_key(settings, timeout=0.1)

        if char == "w":
            teleop_robot.direction = "forward"
            press_key = True
        elif char == "s":
            teleop_robot.direction = "backward"
            press_key = True
        elif char == "a":
            teleop_robot.direction = "left"
            press_key = True
        elif char == "d":
            teleop_robot.direction = "right"
            press_key = True
        elif char == "q":
            break
        else:
            press_key = False

    rclpy.shutdown()

if __name__ == "__main__":
    main()