import base64
import json

import rclpy
from rclpy.node import Node
from computer_vision_interface.srv import FaceRecognition, DescribeEnvironment, GetDistanceClosestObject
import face_recognition
import anthropic



class ComputerVisionEngine(Node):
    def __init__(self, name):
        super().__init__(name)

        self.face_recognition_service = self.create_service(FaceRecognition, 
                                                            'face_recognition', 
                                                            self.face_recognition_callback)

        self.describe_environment_service = self.create_service(DescribeEnvironment, 
                                                                'describe_environment', 
                                                                self.describe_environment_callback)
        
        self.get_distance_closest_object_service = self.create_service(GetDistanceClosestObject, 
                                                                        'get_distance_closest_object', 
                                                                        self.get_distance_closest_object_callback)
        

        self.ai_client = anthropic.Anthropic()

        self.felipe_image = face_recognition.load_image_file("/home/felipe/felipe.png")
        self.felipe_encoding = face_recognition.face_encodings(self.felipe_image)[0]

    def get_claude_response(self, image_path, prompt):
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

        return message.content[0].text

    def get_distance_closest_object_callback(self, request, response):
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
        estimated_distance_cm = int(json.loads(self.get_claude_response(request.image_path, prompt))["estimated_distance_cm"])

        response.distance = estimated_distance_cm

        return response


    def face_recognition_callback(self, request, response):
        
        unknown_image = face_recognition.load_image_file(request.image_path)

        face_locations = face_recognition.face_locations(unknown_image)
        if len(face_locations) == 0:
            response.person_in_image = False
            response.identity = ""
            return response

        unknown_encoding = face_recognition.face_encodings(unknown_image)[0]

        results = face_recognition.compare_faces([self.felipe_encoding], unknown_encoding)

        response.person_in_image = True
        response.identity =  "Felipe" if results[0] else "unknown"
        
        return response

    def describe_environment_callback(self, request, response):
        prompt = "Describe this image with 20 words or less."
        image_description = self.get_claude_response(request.image_path, prompt)

        response.image_description = image_description

        return response

def main(args=None):

    rclpy.init(args=args)
    computer_vision_engine_node = ComputerVisionEngine('computer_vision_engine_node')
    rclpy.spin(computer_vision_engine_node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()