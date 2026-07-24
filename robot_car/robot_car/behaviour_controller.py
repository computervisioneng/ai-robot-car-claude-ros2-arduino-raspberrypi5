import time
import random
import base64
import json
import os
from pathlib import Path

import rclpy
from rclpy.node import Node
from teleop_interface.msg import Teleop
from ui_interface.msg import PlayAudio, DisplayImage
from computer_vision_interface.srv import FaceRecognition, DescribeEnvironment, GetDistanceClosestObject
import cv2
from rcl_interfaces.msg import SetParametersResult
import anthropic

Teleop
class BehaviourController(Node):
    def __init__(self, name):
        super().__init__(name)

        self.declare_parameter("mode", "patrol")
        self.mode = self.get_parameter("mode").get_parameter_value().string_value

        self.valid_modes = ["explore", "patrol", "hide_and_seek"]

        self.add_on_set_parameters_callback(self.parameter_callback)

        self.publisher_teleop = self.create_publisher(Teleop, "teleop_robot_cmds", 10)
        self.publisher_voice = self.create_publisher(PlayAudio, "voice_cmds", 10)
        self.publisher_display = self.create_publisher(DisplayImage, "display_cmds", 10)

        self.face_recognition_client = self.create_client(FaceRecognition, 'face_recognition')
        self.get_distance_closest_object_client = self.create_client(GetDistanceClosestObject, 'get_distance_closest_object')
        self.describe_environment_client = self.create_client(DescribeEnvironment, 'describe_environment')

        while not self.face_recognition_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for face recognition service...")
        while not self.get_distance_closest_object_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for get distance closest object service...")
        while not self.describe_environment_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("Waiting for describe environment service...")

        self.video_cap = cv2.VideoCapture(0)
        self.video_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.intrussion_detected = False
        self.felipe_detected = False

        self.ai_client = anthropic.Anthropic()

        self.timer = self.create_timer(1, self.behaviour_callback)

    def parameter_callback(self, params):
        for param in params:
            if param.name == "mode":
                if param.value not in self.valid_modes:
                    return SetParametersResult(
                        successful=False,
                        reason=f"'mode' needs to be in ['explore', 'patrol', 'hide_and_seek']"
                    )
        return SetParametersResult(successful=True)

    def behaviour_callback(self):

        self.mode = self.get_parameter("mode").get_parameter_value().string_value

        ret, frame = self.video_cap.read()
        tic = time.time()
        while ret:
            ret, frame = self.video_cap.read()
            if time.time() - tic > 1:
                break

        frame_path = '/home/felipe/tmp.png'
        cv2.imwrite(frame_path, frame)

        if self.mode == "explore":
            self.wander(frame_path)
            self.describe_environment(frame_path)

        elif self.mode == "patrol":
            person = FaceRecognition.Request()
            person.image_path = frame_path

            future = self.face_recognition_client.call_async(person)
            future.add_done_callback(self.face_recognition_client_response_patrol_callback)

            if self.intrussion_detected:
                self.get_logger().info('intrussion_detected')
                self.respond_to_intrussion()
            else:
                self.get_logger().info('wander!')
                self.wander(frame_path)
        
        elif self.mode == "hide_and_seek":
            person = FaceRecognition.Request()
            person.image_path = frame_path

            future = self.face_recognition_client.call_async(person)
            future.add_done_callback(self.face_recognition_client_response_hide_and_seek_callback)

            if self.felipe_detected:
                self.get_logger().info('I am so happy! I found Felipe! :)')
                self.celebrate()
            else:
                self.get_logger().info('wander!')
                self.wander(frame_path)

    def celebrate(self):
        # stop motors
        msg_motor = Teleop()
        msg_motor.direction = "stop"
        msg_motor.duration = 100
        msg_motor.speed = 255
        self.publisher_teleop.publish(msg_motor)

        # sound alarm
        msg_audio = PlayAudio()
        msg_audio.audio_path = "/home/felipe/yay.mp3"
        self.publisher_voice.publish(msg_audio)

        # display image
        msg_display = DisplayImage()
        msg_display.image_path = "/home/felipe/celebrate.png"
        self.publisher_display.publish(msg_display)

    def respond_to_intrussion(self):
        # stop motors
        msg_motor = Teleop()
        msg_motor.direction = "stop"
        msg_motor.duration = 100
        msg_motor.speed = 255
        self.publisher_teleop.publish(msg_motor)

        # sound alarm
        msg_audio = PlayAudio()
        msg_audio.audio_path = "/home/felipe/alarm.mp3"
        self.publisher_voice.publish(msg_audio)

        # display image
        msg_display = DisplayImage()
        msg_display.image_path = "/home/felipe/respond_to_intrussion.png"
        self.publisher_display.publish(msg_display)

    def face_recognition_client_response_patrol_callback(self, future):
        result = future.result()

        if result.person_in_image:
            self.intrussion_detected = True
        else:
            self.intrussion_detected = False

    def face_recognition_client_response_hide_and_seek_callback(self, future):
        result = future.result()

        if result.person_in_image and result.identity == "Felipe":
            self.felipe_detected = True
        else:
            self.felipe_detected = False
    
    def describe_environment(self, image_path):
        environment = DescribeEnvironment.Request()
        environment.image_path = image_path

        future = self.describe_environment_client.call_async(environment)
        future.add_done_callback(self.describe_environment_client_response_callback)

    def describe_environment_client_response_callback(self, future):
        described_environment = future.result()

        self.get_logger().info(f"Environment: {described_environment}")


    def get_distance_closest_object(self, image_path):
        prompt = """
        You are a robot with a frontal camera view.

        You do not have precise distance measurement, only rough visual judgment based on object size, occlusion, and perspective.

        Estimate the distance in cm to the closest object directly ahead in your path.

        If the camera view is completely blocked or unreadable (e.g. covered, too dark, too close to an object), set estimated_distance_cm to 0.

        Respond with ONLY a single JSON object, no markdown, no code fences, no explanation, no extra text.
        estimated_distance_cm must be an integer.

        Example output:
        {"estimated_distance_cm": 120}
        """

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        message = self.ai_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        estimated_distance_cm = int(json.loads(message.content[0].text)["estimated_distance_cm"])

        return estimated_distance_cm

    def wander(self, image_path):
        msg_display = DisplayImage()
        if self.mode == "explore":
            msg_display.image_path = '/home/felipe/wander_explore.png'
        elif self.mode == "patrol":
            msg_display.image_path = '/home/felipe/wander_patrol.png'
        elif self.mode == "hide_and_seek":
            msg_display.image_path = '/home/felipe/wander_hide_and_seek.png'
        self.publisher_display.publish(msg_display)

        msg_audio = PlayAudio()
        msg_audio.audio_path = ''
        self.publisher_voice.publish(msg_audio)

        # TODO: calling the service sync creates a deadlock, async doesn't fit this project very well. 
        distance_to_object = self.get_distance_closest_object(image_path)
        self.get_logger().info(f'Distance closest object: {distance_to_object}')

        msg_teleop = Teleop()

        if distance_to_object > 15:
            random_ = random.random()
            msg_teleop.direction = "forward" if random_ < 0.5 else "left" if random_ < 0.75 else "right"
        else:
            msg_teleop.direction = "backward"

        msg_teleop.duration = 300 + int(random.random() * 500)

        msg_teleop.speed = 255

        self.publisher_teleop.publish(msg_teleop)


def main(args=None):

    rclpy.init(args=args)
    behaviour_controller = BehaviourController('behaviour_controller_node')

    rclpy.spin(behaviour_controller)

    rclpy.shutdown()

if __name__ == "__main__":
    main()