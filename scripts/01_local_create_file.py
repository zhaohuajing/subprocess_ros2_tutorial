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
