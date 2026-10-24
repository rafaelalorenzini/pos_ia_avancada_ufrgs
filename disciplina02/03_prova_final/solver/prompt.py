"""Everything about the prompts: turning a task into text, and reading the model's answer back.

There is one prompt per approach:
    end to end       the model writes the output grid(s) directly, as JSON
    code generation  the model writes a Python function transform(grid)
"""

import json
import re

from validator import is_grid


def grid_to_text(grid):
    """Turn [[1, 0], [0, 1]] into the lines "1 0" and "0 1"."""
    return "\n".join(" ".join(str(cell) for cell in row) for row in grid)


def describe_task(task):
    """The part both prompts share: the introduction, the training pairs and the test inputs."""
    lines = [
        "You are solving an ARC-AGI puzzle.",
        "Each grid is a matrix of integers from 0 to 9; each number is a color.",
        "Study the training examples and find the single transformation rule that",
        "turns every input into its output.",
        "",
    ]
    for i, pair in enumerate(task["train"], start=1):
        lines += [
            f"## Training example {i}",
            "Input:",
            grid_to_text(pair["input"]),
            "Output:",
            grid_to_text(pair["output"]),
            "",
        ]
    for i, pair in enumerate(task["test"], start=1):
        lines += [f"## Test input {i}", grid_to_text(pair["input"]), ""]
    return lines


# ---------------------------------------------------------------------------
# End to end: the model writes the grids
# ---------------------------------------------------------------------------

def build_direct_prompt(task):
    lines = describe_task(task) + [
        "## Task",
        "Apply the rule to the test input(s).",
        "",
        "## Answer format",
        "Reply with only a JSON object and nothing else:",
        '{"rule_summary": "<one or two sentences describing the rule>",',
        ' "test_outputs": [<output grid for test input 1>, ...]}',
        "Each output grid is a list of rows; each row is a list of integers.",
    ]
    return "\n".join(lines)


def parse_direct_answer(text):
    """Find the JSON object in the reply (models often wrap it in ```json fences).

    Raises ValueError (json.JSONDecodeError is one) when there is no usable JSON.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in the model reply")
    answer = json.loads(match.group(0))
    test_outputs = answer.get("test_outputs", [])
    # With a single test input the model sometimes sends the grid itself instead of a list of grids.
    if is_grid(test_outputs):
        test_outputs = [test_outputs]
    return {
        "rule_summary": answer.get("rule_summary", ""),
        "test_outputs": test_outputs,
    }


# ---------------------------------------------------------------------------
# Code generation: the model writes transform(grid)
# ---------------------------------------------------------------------------

def build_code_prompt(task):
    lines = describe_task(task) + [
        "## Task",
        "Write a Python function transform(grid) that implements the rule.",
        "It receives one input grid (a list of rows; each row is a list of integers)",
        "and must return the output grid in the same format.",
        "It must work for every training example and for the test input(s).",
        "You may use the standard library, numpy and scipy. Do not read files or print.",
        "",
        "## Answer format",
        "Reply with a single ```python code block containing the function",
        "(plus any imports and helpers it needs), and nothing else.",
    ]
    return "\n".join(lines)


def extract_code(text):
    """Take the Python code out of the reply: the last fenced block that defines transform.

    Raises ValueError when the reply has no transform function.
    """
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    for block in reversed(blocks):
        if "def transform" in block:
            return block.strip()
    if "def transform" in text:  # no fences at all: assume the whole reply is code
        return text.strip()
    raise ValueError("no transform(grid) function found in the model reply")
