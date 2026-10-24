"""Running the transform(grid) written by the model, with a time limit.

Each call starts a separate Python process, so a program that loops forever, crashes
or messes with global state cannot hurt the solver: we simply kill it at the deadline.
This is isolation against accidents, not a security sandbox.
"""

import json
import subprocess
import sys
import tempfile

TIMEOUT_SECONDS = 10

# The code run inside the child process. It reads {"code", "grid"} from stdin and writes
# {"output"} or {"error"} to stdout. Anything the model's code prints goes to stderr instead,
# so it cannot corrupt the JSON answer.
RUNNER = r"""
import json, sys, traceback
real_stdout, sys.stdout = sys.stdout, sys.stderr
job = json.load(sys.stdin)

def to_grid(value):
    if hasattr(value, "tolist"):  # numpy arrays
        value = value.tolist()
    grid = [list(row) for row in value]
    for row in grid:
        for i, cell in enumerate(row):
            if int(cell) != cell:
                raise ValueError(f"cell {cell!r} is not an integer")
            row[i] = int(cell)
    return grid

try:
    namespace = {"__name__": "generated"}
    exec(job["code"], namespace)
    output = to_grid(namespace["transform"](job["grid"]))
    result = {"output": output}
except Exception as error:
    lines = traceback.format_exception_only(type(error), error)
    result = {"error": "".join(lines).strip()}
real_stdout.write(json.dumps(result))
"""


def run_transform(code, grid, timeout=TIMEOUT_SECONDS):
    """Run transform(grid) in a child process. Returns (output_grid, None) or (None, error)."""
    try:
        process = subprocess.run(
            [sys.executable, "-I", "-c", RUNNER],
            input=json.dumps({"code": code, "grid": grid}),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
        )
    except subprocess.TimeoutExpired:
        return None, f"timeout: took more than {timeout} s"
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError:
        stderr = process.stderr.strip().splitlines()
        return None, f"the program crashed: {stderr[-1] if stderr else 'no output'}"
    return result.get("output"), result.get("error")
