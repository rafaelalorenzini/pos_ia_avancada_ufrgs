"""Everything about the prompt: turning a task into text, and reading the model's answer back."""

import json
import re


def grid_to_text(grid):
    """Turn [[1, 0], [0, 1]] into the lines "1 0" and "0 1"."""
    return "\n".join(" ".join(str(cell) for cell in row) for row in grid)


def build_prompt(task):
    lines = [
        "You are solving an ARC-AGI puzzle.",
        "Each grid is a matrix of integers from 0 to 9; each number is a color.",
        "Study the training examples, find the single transformation rule that",
        "turns every input into its output, then apply it to the test input(s).",
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
    lines += [
        "## Answer format",
        "Reply with only a JSON object and nothing else:",
        '{"rule_summary": "<one or two sentences describing the rule>",',
        ' "test_outputs": [<output grid for test input 1>, ...]}',
        "Each output grid is a list of rows; each row is a list of integers.",
    ]
    return "\n".join(lines)


def parse_answer(text):
    """Find the JSON object in the reply (models often wrap it in ```json fences).

    Raises ValueError (json.JSONDecodeError is one) when there is no usable JSON.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in the model reply")
    answer = json.loads(match.group(0))
    return {
        "rule_summary": answer.get("rule_summary", ""),
        "test_outputs": answer.get("test_outputs", []),
    }
