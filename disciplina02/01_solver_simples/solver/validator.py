"""Check a solver answer against the expected outputs of an ARC-AGI task.

Usage:
    uv run solver/validator.py ../data/training/<task>.json outputs/<run>/answer.json

For each test input it reports whether the predicted grid is exactly right,
and if not, whether the shape matches and how many cells are correct.
The exit code is 0 when every test output is correct, 1 otherwise.
"""

import argparse
import json
import sys
from pathlib import Path


def is_grid(value):
    """A grid is a non-empty list of equally long lists of integers."""
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(row, list) and len(row) == len(value[0]) for row in value)
        and all(isinstance(cell, int) for row in value for cell in row)
    )


def show(title, grid):
    print(f"  {title}:")
    for row in grid:
        print("    " + " ".join(str(cell) for cell in row))


def check(expected, predicted):
    """Print the comparison for one test input and return True if it is exactly right."""
    if not is_grid(predicted):
        print("  WRONG: the prediction is missing or is not a valid grid")
        show("expected", expected)
        return False
    if predicted == expected:
        print("  CORRECT")
        return True

    expected_shape = (len(expected), len(expected[0]))
    predicted_shape = (len(predicted), len(predicted[0]))
    show("expected", expected)
    show("predicted", predicted)
    if predicted_shape != expected_shape:
        print(f"  WRONG: shape {predicted_shape}, expected {expected_shape}")
        return False

    # Same shape: mark each cell "." when right and "X" when wrong.
    diff = [["." if p == e else "X" for p, e in zip(p_row, e_row)] for p_row, e_row in zip(predicted, expected)]
    right = sum(row.count(".") for row in diff)
    total = expected_shape[0] * expected_shape[1]
    show("diff (X = wrong cell)", diff)
    print(f"  WRONG: {right}/{total} cells correct ({right / total:.0%})")
    return False


def main():
    parser = argparse.ArgumentParser(description="Validate a solver answer for an ARC-AGI task.")
    parser.add_argument("task", type=Path, help="path to the ARC task JSON")
    parser.add_argument("answer", type=Path, help="path to the answer.json written by main.py")
    args = parser.parse_args()

    for path in (args.task, args.answer):
        if not path.is_file():
            sys.exit(f"File not found: {path}\nRun main.py first and use the answer.json path it prints.")

    task = json.loads(args.task.read_text(encoding="utf-8"))
    answer = json.loads(args.answer.read_text(encoding="utf-8"))
    predictions = answer.get("test_outputs", [])

    print(f"Rule summary: {answer.get('rule_summary') or '(none)'}")
    if "error" in answer:
        print(f"Solver error: {answer['error']}")

    results = []
    for i, test in enumerate(task["test"]):
        print(f"\nTest {i + 1}")
        if "output" not in test:
            print("  SKIPPED: the task file has no expected output for this test")
            results.append(False)
            continue
        predicted = predictions[i] if i < len(predictions) else None
        results.append(check(test["output"], predicted))

    print(f"\nScore: {sum(results)}/{len(results)} test outputs correct")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
