#!/usr/bin/env python3
import subprocess
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
output_dir = project_root / "outputs"
output_dir.mkdir(exist_ok=True)
output_file = output_dir / "demo_output.txt"

cmd = [
    "bash",
    "-lc",
    f"echo 'Hello from subprocess' > '{output_file}'"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Created file:", output_file)
