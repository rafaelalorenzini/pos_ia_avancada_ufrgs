"""Check predicted grids against the expected outputs of an ARC-AGI task.

main.py uses validate() to score each task. You can also run this file on its own
to see a detailed, cell-by-cell comparison of a saved answer:

    uv run solver/validator.py tarefas/training/3aa6fb7a.json resultados/<run>/direct/3aa6fb7a/answer.json
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


def validate(task, predictions):
    """Return one True/False per test input: is the predicted grid exactly right?"""
    results = []
    for i, test in enumerate(task["test"]):
        predicted = predictions[i] if i < len(predictions) else None
        results.append(is_grid(predicted) and predicted == test.get("output"))
    return results


# ---------------------------------------------------------------------------
# Detailed report, used when this file is run directly
# ---------------------------------------------------------------------------

def show(title, grid):
    print(f"  {title}:")
    for row in grid:
        print("    " + " ".join(str(cell) for cell in row))


def report(expected, predicted):
    """Print the comparison for one test input."""
    if not is_grid(predicted):
        print("  WRONG: the prediction is missing or is not a valid grid")
        show("expected", expected)
        return
    if predicted == expected:
        print("  CORRECT")
        return

    expected_shape = (len(expected), len(expected[0]))
    predicted_shape = (len(predicted), len(predicted[0]))
    show("expected", expected)
    show("predicted", predicted)
    if predicted_shape != expected_shape:
        print(f"  WRONG: shape {predicted_shape}, expected {expected_shape}")
        return

    # Same shape: mark each cell "." when right and "X" when wrong.
    diff = [["." if p == e else "X" for p, e in zip(p_row, e_row)] for p_row, e_row in zip(predicted, expected)]
    right = sum(row.count(".") for row in diff)
    total = expected_shape[0] * expected_shape[1]
    show("diff (X = wrong cell)", diff)
    print(f"  WRONG: {right}/{total} cells correct ({right / total:.0%})")


def main():
    parser = argparse.ArgumentParser(description="Validate a saved answer for an ARC-AGI task.")
    parser.add_argument("task", type=Path, help="path to the ARC task JSON")
    parser.add_argument("answer", type=Path, help="path to an answer.json written by main.py")
    args = parser.parse_args()

    for path in (args.task, args.answer):
        if not path.is_file():
            sys.exit(f"File not found: {path}")

    task = json.loads(args.task.read_text(encoding="utf-8"))
    answer = json.loads(args.answer.read_text(encoding="utf-8"))
    predictions = answer.get("test_outputs", [])

    print(f"Rule summary: {answer.get('rule_summary') or '(none)'}")
    for i, test in enumerate(task["test"]):
        print(f"\nTest {i + 1}")
        predicted = predictions[i] if i < len(predictions) else None
        report(test["output"], predicted)

    results = validate(task, predictions)
    print(f"\nScore: {sum(results)}/{len(results)} test outputs correct")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
