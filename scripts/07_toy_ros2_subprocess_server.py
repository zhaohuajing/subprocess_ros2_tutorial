#!/usr/bin/env python3

import subprocess
import rclpy
from rclpy.node import Node
from example_interfaces.srv import Trigger


class ToySubprocessServer(Node):
    def __init__(self):
        super().__init__("toy_subprocess_server")
        self.srv = self.create_service(Trigger, "/make_demo_file", self.callback)
        self.get_logger().info("Toy subprocess server is ready.")

    def callback(self, request, response):
        cmd = [
            "bash",
            "-lc",
            "echo 'Created by ROS 2 subprocess server' > /tmp/ros2_demo.txt"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            response.success = False
            response.message = result.stderr
            return response

        response.success = True
        response.message = "Created /tmp/ros2_demo.txt successfully."
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ToySubprocessServer()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
