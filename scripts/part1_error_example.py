#!/usr/bin/env python3
import subprocess

cmd = ["bash", "-lc", "cat file_that_does_not_exist.txt"]
result = subprocess.run(cmd, capture_output=True, text=True)

print("Return code:", result.returncode)
print("STDERR:", result.stderr)
