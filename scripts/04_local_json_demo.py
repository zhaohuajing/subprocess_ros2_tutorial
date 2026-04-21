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
