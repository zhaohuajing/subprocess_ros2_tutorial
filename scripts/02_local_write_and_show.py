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
