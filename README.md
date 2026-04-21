# Using Python `subprocess` to Build ROS 2 Wrappers for Dockerized Perception and Grasp-Planning Modules

## Overview

This tutorial shows how to use Python's `subprocess` module to wrap an external perception or grasp-planning module and expose it cleanly to a ROS 2 system. The core motivating example is a ROS 2 service wrapper around Contact-GraspNet, where the ROS 2 server runs on the host machine while grasp inference executes inside a Docker container with its own Python and CUDA environment.

This pattern is especially useful when:

- ROS 2 on the host depends on one environment, for example Python 3.12 and CUDA 12.x.
- The external open-source module depends on a different environment, for example Python 3.9 and CUDA 11.x.
- You want other ROS 2 nodes to call the module through a normal ROS 2 service instead of manually entering containers or shell commands.

The same wrapper strategy can be reused for other components such as UnseenObjectClustering, segmentation modules, or custom learned planners.

## Learning goals

By the end of this tutorial, you should be able to:

- understand the role of `subprocess.run()` in Python
- launch simple shell commands from Python
- capture standard output and standard error
- execute commands inside a Docker container from a host script
- understand why `bash -lc` is often used in subprocess-driven wrappers
- build a simple ROS 2 service server that delegates work through `subprocess`
- understand the structure of a Contact-GraspNet ROS 2 service wrapper

## Why `subprocess` is useful here

The `subprocess` module lets a Python program run external commands, wait for them to finish, inspect whether they succeeded, and capture their outputs. In robotics integration work, this is valuable because many open-source modules are not packaged as importable Python libraries that match your host environment. Some require old Python versions, old CUDA stacks, Conda environments, or Docker images.

Instead of forcing everything into a single environment, you can use this design:

- host Python script or ROS 2 node acts as the orchestrator
- `subprocess` launches a command in the required runtime
- results are captured and translated into ROS 2 messages

In other words, the host stays in control, while execution happens where the external module can actually run.

---

## Part 1. Minimal example: create a file locally with `subprocess`

We begin with a very simple example. The goal is to show that Python can launch a shell command that creates a file and writes text into it.

Save the following as `01_local_create_file.py`:

```python
import subprocess

cmd = [
    "bash",
    "-lc",
    "echo 'Hello from subprocess' > demo_output.txt"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
```

### Run it

```bash
python3 01_local_create_file.py
cat demo_output.txt
```

### What to observe

You should see:

- return code `0`, which means success
- a new file named `demo_output.txt`
- the file contains the text `Hello from subprocess`

### Discussion

This example introduces a few important pieces:

- `cmd` is the command that will be executed
- `capture_output=True` tells Python to capture stdout and stderr
- `text=True` returns stdout and stderr as strings instead of bytes

Here, the command is run through:

```bash
bash -lc "..."
```

This is helpful because it allows you to use normal shell syntax, including output redirection (`>`), chaining with `&&`, and command substitution if needed later.

---

## Part 2. A slightly richer local example: write and display file contents

Now let us chain multiple shell actions together.

Save the following as `02_local_write_and_show.py`:

```python
import subprocess

cmd = [
    "bash",
    "-lc",
    "echo 'Line 1' > demo_output.txt && "
    "echo 'Line 2' >> demo_output.txt && "
    "cat demo_output.txt"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
```

### Run it

```bash
python3 02_local_write_and_show.py
```

### What to observe

The script should print:

- `Line 1`
- `Line 2`

This shows that `subprocess` can be used not only to launch a single command, but to launch a short shell workflow.

---

## Part 3. Handling errors

A wrapper is only useful if it can detect and report failure cleanly.

Save the following as `03_local_error_demo.py`:

```python
import subprocess

cmd = ["bash", "-lc", "cat file_that_does_not_exist.txt"]
result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDERR:")
print(result.stderr)
```

### Run it

```bash
python3 03_local_error_demo.py
```

### What to observe

You should see a nonzero return code and an error message in stderr.

This is important because later, when a ROS 2 server launches inference in Docker, it should not silently continue if the external process fails. It should detect the nonzero return code and raise or log an informative error.

---

## Part 4. Returning structured output through stdout

Many wrappers need more than plain text. They need machine-readable results. A common solution is to print JSON from the external process and parse it in the host script.

Save the following as `04_local_json_demo.py`:

```python
import subprocess
import json

cmd = [
    "python3",
    "-c",
    (
        "import json; "
        "print(json.dumps({'status': 'ok', 'message': 'hello', 'values': [1, 2, 3]}))"
    )
]

result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    raise RuntimeError(result.stderr)

data = json.loads(result.stdout)
print("Parsed JSON:", data)
```

### Run it

```bash
python3 04_local_json_demo.py
```

### What to observe

The script should print a parsed Python dictionary.

This is the same general idea that will later be used in the Contact-GraspNet ROS 2 wrapper: run an external command, collect stdout, and parse JSON from it.

---

## Part 5. Running a command inside Docker from the host

Now we keep the host script in Python, but ask it to do work inside a running Docker container.

For this stage, assume you already have a running container named `demo_container`.

Save the following as `05_docker_create_file.py`:

```python
import subprocess

container_name = "demo_container"

cmd = [
    "docker", "exec", container_name,
    "bash", "-lc",
    "echo 'Hello from inside Docker' > /tmp/docker_demo.txt && cat /tmp/docker_demo.txt"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
```

### Run it

```bash
python3 05_docker_create_file.py
docker exec demo_container bash -lc "cat /tmp/docker_demo.txt"
```

### What to observe

The host script launches `docker exec`, which enters the container and runs the shell command there. The file is created inside the container, but the output still comes back to the host through stdout.

### Why this matters

This is the key integration pattern:

- host Python stays in the host environment
- target module runs inside Docker
- results come back through captured stdout or files

---

## Part 6. Using a shared host-container folder

In many real systems, the host prepares an input file, the container processes it, and the result appears in a shared mounted directory.

Assume a host directory is mounted into the container like this:

- host: `~/demo_shared`
- container: `/workspace/shared`

Save the following as `06_docker_shared_volume_demo.py`:

```python
import subprocess
from pathlib import Path

host_file = Path.home() / "demo_shared" / "input.txt"
host_file.parent.mkdir(parents=True, exist_ok=True)
host_file.write_text("This file was created on the host.\n")

container_name = "demo_container"

cmd = [
    "docker", "exec", container_name,
    "bash", "-lc",
    "cat /workspace/shared/input.txt > /workspace/shared/output.txt && "
    "echo 'Processed in Docker' >> /workspace/shared/output.txt"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDERR:", result.stderr)
```

### Run it

```bash
python3 06_docker_shared_volume_demo.py
cat ~/demo_shared/output.txt
```

### What to observe

You should see that:

- the host creates the input file
- the container reads it
- the container writes the output file
- the host can inspect the result immediately

This is conceptually similar to how a ROS 2 wrapper may prepare input data, call inference inside Docker, and then load results from stdout or shared files.

---

## Part 7. Transition to ROS 2 wrappers

At this point we have already demonstrated the core pattern:

1. Python on the host launches a command
2. the command can run locally or inside Docker
3. the host checks success and reads outputs
4. structured results can be parsed and reused

To turn this into a ROS 2 integration, we place the `subprocess` call inside a ROS 2 service server.

Then a ROS 2 client can simply call a service such as `/get_grasps` without needing to know anything about:

- Docker commands
- Conda environments
- exact file paths
- model-specific shell syntax

The ROS 2 server becomes the adapter between the ROS ecosystem and the external module.

---

## Part 8. A toy ROS 2 service wrapper using `subprocess`

Before looking at Contact-GraspNet, it is helpful to build a tiny ROS 2 service example.

The following example assumes you already have a custom service type available, or that you will adapt the logic to your own package. The purpose here is to show the structure rather than impose a specific package layout.

Save the following as `07_toy_ros2_subprocess_server.py`:

```python
#!/usr/bin/env python3

import subprocess
import rclpy
from rclpy.node import Node

# Replace this import with your own service type
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
```

### Example run pattern

In one terminal:

```bash
ros2 run <your_package> 07_toy_ros2_subprocess_server.py
```

In another terminal:

```bash
ros2 service call /make_demo_file example_interfaces/srv/Trigger
cat /tmp/ros2_demo.txt
```

### What this teaches

This example is intentionally simple, but the pattern is the same as a more advanced wrapper:

- ROS 2 callback receives a request
- callback launches external work through `subprocess`
- callback checks whether it succeeded
- callback returns a ROS 2 response

---

## Part 9. Case study: Contact-GraspNet ROS 2 wrapper

Now we look at the full motivation for this tutorial.

### Goal

We want a ROS 2 service server on the host that can receive a request such as a scene name, run Contact-GraspNet inference inside a Docker container, parse the result, and return grasps as a ROS 2 message.

### Why this design is useful

This design allows us to:

- keep ROS 2 running on the host system
- keep Contact-GraspNet in a controlled Docker environment
- avoid dependency conflicts between host ROS 2 and model runtime
- expose the module through a clean ROS 2 service interface

### Key design idea

The host ROS 2 server does not import Contact-GraspNet directly. Instead, it uses `subprocess.run()` to invoke:

```bash
docker exec <container> bash -lc "<commands>"
```

That means the external model runs exactly where it is supported, while the ROS 2 node remains a lightweight controller and translator.

---

## Part 10. Understanding the Contact-GraspNet subprocess block

A representative `run_inference_in_docker()` function looks like this:

```python
def run_inference_in_docker(self, scene_name) -> str:
    container_name = "contact_graspnet_container"
    np_path = f"test_data/{scene_name}.npy"

    compiled_lib = (
        "/root/graspnet_ws/src/contact_graspnet_ros2/contact_graspnet/"
        "pointnet2/tf_ops/sampling/tf_sampling_so.so"
    )

    compile_cmd = (
        f"if [ ! -f {compiled_lib} ]; then "
        f"cd /root/graspnet_ws/src/contact_graspnet_ros2/contact_graspnet && "
        f"conda run -n contact-graspnet bash compile_pointnet_tfops.sh; "
        f"fi"
    )

    inference_cmd = (
        "cd /root/graspnet_ws/src/contact_graspnet_ros2/contact_graspnet && "
        f"conda run -n contact-graspnet python contact_graspnet/inference.py "
        f"--np_path={np_path} --local_regions --filter_grasps"
    )

    cmd = [
        "docker", "exec", container_name,
        "bash", "-lc", f"{compile_cmd} && {inference_cmd}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Inference failed: {result.stderr}")

    start_marker = "<<<BEGIN_JSON>>>"
    end_marker = "<<<END_JSON>>>"

    json_text = None
    start = result.stdout.find(start_marker)
    end = result.stdout.find(end_marker, start)
    if start != -1 and end != -1:
        json_text = result.stdout[start + len(start_marker):end].strip()
    else:
        for line in result.stdout.splitlines():
            if line.strip().startswith("{") and line.strip().endswith("}"):
                json_text = line.strip()
                break

    if json_text is None:
        raise RuntimeError("Inference did not return valid JSON")

    return json_text
```

### Step-by-step explanation

1. **Select the Docker container**

   The wrapper assumes Contact-GraspNet is already available in a running container.

2. **Build the scene-specific input path**

   The request may contain a scene name, which is mapped to an input file such as:

   `test_data/scene_from_ucn.npy`

3. **Optionally compile dependencies**

   The wrapper checks whether the compiled TensorFlow ops already exist. If they do not, it compiles them inside the container.

4. **Build the inference command**

   The wrapper enters the correct working directory and launches Contact-GraspNet using the appropriate Conda environment.

5. **Run everything through `subprocess.run()`**

   The host script calls `docker exec`, which enters the container and runs the shell command.

6. **Check the return code**

   If inference fails, the wrapper raises an error using stderr. This is essential for debugging.

7. **Extract structured output**

   The wrapper searches stdout for JSON markers such as:

   - `<<<BEGIN_JSON>>>`
   - `<<<END_JSON>>>`

   This is good practice because model stdout may contain logs, warnings, and other lines that should not be parsed as the final result.

8. **Return the JSON payload**

   The server can then load the JSON and convert it into ROS 2 message content.

---

## Part 11. Why JSON markers are helpful

When an external model runs, its stdout often contains mixed content:

- progress logs
- package warnings
- diagnostic prints
- final inference results

If you simply try to parse all of stdout as JSON, the parse may fail.

A robust solution is to have the inference script print something like:

```text
<<<BEGIN_JSON>>>
{...actual JSON result...}
<<<END_JSON>>>
```

Then the wrapper can reliably extract only the structured payload.

This is especially useful when wrapping research code, where stdout is often noisy.

---

## Part 12. From parsed output to ROS 2 messages

After JSON is extracted and loaded, the Contact-GraspNet server still has one more important job: translating model output into ROS-native data.

In a typical wrapper, the server will:

- load `pred_grasps_cam`
- load `scores`
- load `contact_pts`
- convert transforms into `geometry_msgs/Pose`
- transform poses into the desired robot base frame
- package everything into a custom ROS 2 message such as `Grasps`
- return the response to the client

This is an important conceptual point:

`subprocess` is the bridge, but the wrapper's real value is in turning external results into ROS 2 data structures that the rest of the system can use.

---

## Part 13. Suggested ROS 2 execution workflow

A typical workflow for the Contact-GraspNet wrapper looks like this:

### Terminal 1: start the Docker container

```bash
docker start contact_graspnet_container
```

or, if needed, launch it with the appropriate image, mounts, and GPU access.

### Terminal 2: run the ROS 2 service server

```bash
ros2 run contact_graspnet_ros2 grasp_executor_rgbd_server
```

### Terminal 3: call the service from a client

```bash
ros2 service call /get_grasps contact_graspnet_ros2/srv/GetGrasps "{scene_name: 'scene_from_ucn'}"
```

### Expected behavior

- the server receives the request
- the server runs inference inside Docker via `subprocess`
- the server parses the returned JSON
- the server converts the results into ROS messages
- the client receives grasp poses, scores, and sample points

---

## Part 14. Best practices for subprocess-based wrappers

When building wrappers like this, the following practices help a lot:

### 1. Keep commands readable

Build `compile_cmd`, `inference_cmd`, and the final `cmd` separately. This makes debugging much easier.

### 2. Always check `returncode`

Do not assume success. If the command fails, expose stderr clearly.

### 3. Capture both stdout and stderr

Even if you mainly expect JSON on stdout, stderr is critical for debugging environment and runtime issues.

### 4. Prefer structured outputs

Use JSON or clearly defined result files rather than ad hoc text parsing.

### 5. Use markers when stdout is noisy

JSON markers greatly reduce fragile parsing.

### 6. Keep ROS 2 independent from the model runtime

The whole point of this pattern is to decouple environments.

### 7. Make mounted paths explicit

Document which folders are shared between host and container.

### 8. Start with a toy wrapper before the full module

It is much easier to debug ROS 2 service logic with a simple file-writing example than with a full learned model.

---

## Part 15. Common debugging tips

### Problem: `docker exec` fails

Check:

```bash
docker ps
docker logs <container_name>
```

Make sure the container is running and has the expected name.

### Problem: file paths do not match

Check that the host and container agree on mounted paths and working directories.

### Problem: `conda run` fails inside Docker

Manually enter the container and test the same command:

```bash
docker exec -it contact_graspnet_container bash
conda run -n contact-graspnet python --version
```

### Problem: no JSON found in stdout

Print the first part of stdout and inspect what the model is actually returning. It may be missing markers or may be printing extra logs around the JSON.

### Problem: ROS 2 service returns but no grasps appear usable

Check the post-processing stages:

- camera-frame convention
- optical-frame to ROS camera frame conversion
- grasp frame to gripper frame offset
- TF transform from camera frame to robot base frame

---

## Part 16. Extending the same pattern to other modules

The same wrapper architecture can be applied to many modules beyond Contact-GraspNet.

For example:

- UnseenObjectClustering
- segmentation or detection modules
- point cloud registration tools
- learned planners in Conda environments
- non-ROS research code that only exposes command-line interfaces

The pattern remains the same:

1. a ROS 2 node receives a request
2. the node launches external work through `subprocess`
3. the node checks success and parses results
4. the node returns ROS-native outputs

This makes it much easier to combine independently developed open-source modules into a modular ROS 2 pipeline.

---

## Part 17. Summary

This tutorial showed a staged path from simple Python subprocess usage to a realistic ROS 2 wrapper for a Dockerized grasp-planning module.

The key takeaway is that `subprocess` provides a practical bridge between:

- a stable ROS 2 host environment
- an external module's required runtime
- a clean ROS 2 service interface for the rest of the system

For research integration, benchmarking, and modular pipeline development, this is often a much more practical strategy than trying to force every dependency into a single environment.

---

## Appendix A. Quick command checklist

### Local examples

```bash
python3 01_local_create_file.py
python3 02_local_write_and_show.py
python3 03_local_error_demo.py
python3 04_local_json_demo.py
```

### Docker examples

```bash
python3 05_docker_create_file.py
python3 06_docker_shared_volume_demo.py
```

### ROS 2 toy example

```bash
ros2 run <your_package> 07_toy_ros2_subprocess_server.py
ros2 service call /make_demo_file example_interfaces/srv/Trigger
```

### Contact-GraspNet wrapper pattern

```bash
docker start contact_graspnet_container
ros2 run contact_graspnet_ros2 grasp_executor_rgbd_server
ros2 service call /get_grasps contact_graspnet_ros2/srv/GetGrasps "{scene_name: 'scene_from_ucn'}"
```

---

## Appendix B. Suggested next improvements

If you expand this tutorial later, useful next additions would be:

- a companion ROS 2 client example
- a version using `.npz` result loading instead of JSON
- a section on using `subprocess.Popen` for long-running processes
- a comparison of subprocess wrappers versus direct Python imports
- a second case study using UnseenObjectClustering