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
