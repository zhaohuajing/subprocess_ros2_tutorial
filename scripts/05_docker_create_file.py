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
