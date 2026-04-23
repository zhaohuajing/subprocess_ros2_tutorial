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
    f"echo 'Line 1: Hello from subprocess' > '{output_file}' && echo 'Line 2: Hello from subprocess again' >> '{output_file}' && cat '{output_file}'"
]

result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
print("Created file:", output_file)
