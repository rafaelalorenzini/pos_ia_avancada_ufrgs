"""A complete but simple and educational ARC-AGI-1 solver. This is the entry point.

Usage (run from this folder):
    uv run main.py 007bbfb7                          # one task, by id
    uv run main.py ../data/training/007bbfb7.json    # one task, by path
    uv run main.py tasks.txt --label baseline        # several tasks + summary.json
    uv run main.py tasks.txt --provider openrouter

How it works, for each task:
    1. prompt.py    turns the task into a prompt
    2. llm.py       sends it to Gemini 3.5 Flash Lite (reasoning: high)
    3. prompt.py    reads the rule summary and the predicted grids from the reply
    4. validator.py checks the grids against the expected outputs

Everything is saved in results/<label>_<timestamp>/:
    <task_id>/prompt.txt    the exact prompt sent to the model
    <task_id>/response.txt  the raw reply of the model
    <task_id>/answer.json   rule summary, predicted grids, tokens, correct or not
    summary.json            the whole experiment (only when a tasks .txt is given)
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

import llm
from prompt import build_prompt, parse_answer
from validator import validate

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT.parent / "data"
RESULTS_DIR = ROOT / "results"
WAIT_SECONDS = 10


# ---------------------------------------------------------------------------
# Finding the tasks
# ---------------------------------------------------------------------------

def find_task(entry):
    """Accept a path to a task JSON, or just a task id like "007bbfb7"."""
    path = Path(entry)
    if path.is_file():
        return path
    for folder in ("training", "evaluation"):
        candidate = DATA_DIR / folder / f"{path.stem}.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"task not found: {entry}")


def read_task_list(tasks_file):
    """One task per line; blank lines and # comments are ignored."""
    lines = Path(tasks_file).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


# ---------------------------------------------------------------------------
# Solving one task
# ---------------------------------------------------------------------------

def solve(task_path, provider, run_dir):
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task_dir = run_dir / task_path.stem
    task_dir.mkdir(parents=True)

    prompt = build_prompt(task)
    (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    result = {
        "task_id": task_path.stem,
        "correct": False,
        "tests_correct": [],
        "rule_summary": "",
        "tokens": {"input": 0, "reasoning": 0, "answer": 0},
        "seconds": 0.0,
        "error": None,
    }
    start = time.time()
    try:
        reply, result["tokens"] = llm.ask(prompt, provider)
        (task_dir / "response.txt").write_text(reply, encoding="utf-8")
        answer = parse_answer(reply)
        result["rule_summary"] = answer["rule_summary"]
        result["tests_correct"] = validate(task, answer["test_outputs"])
        result["correct"] = all(result["tests_correct"])
    except Exception as error:  # keep going: one bad task should not stop an experiment
        answer = {"rule_summary": "", "test_outputs": []}
        result["error"] = f"{type(error).__name__}: {error}"
    result["seconds"] = round(time.time() - start, 1)

    (task_dir / "answer.json").write_text(json.dumps({**answer, **result}, indent=2), encoding="utf-8")
    return result


def print_result(result):
    t = result["tokens"]
    print(f"  tokens: input {t['input']} | reasoning {t['reasoning']} | answer {t['answer']}")
    if result["error"]:
        print(f"  result: ERROR ({result['error']})")
    else:
        tests = result["tests_correct"]
        verdict = "SOLVED" if result["correct"] else "NOT SOLVED"
        print(f"  result: {verdict} ({sum(tests)}/{len(tests)} test outputs correct, {result['seconds']} s)")


# ---------------------------------------------------------------------------
# Running an experiment
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Solve ARC-AGI-1 tasks with Gemini 3.5 Flash Lite.")
    parser.add_argument("tasks", help="a task id, a task JSON path, or a .txt file listing tasks")
    parser.add_argument("--provider", choices=llm.PROVIDERS, default="google")
    parser.add_argument("--label", default="experiment", help="a name for this experiment")
    args = parser.parse_args()

    load_dotenv(find_dotenv())  # looks for .env here and in the parent folders

    from_file = args.tasks.endswith(".txt")
    entries = read_task_list(args.tasks) if from_file else [args.tasks]
    task_paths = [find_task(entry) for entry in entries]

    started = datetime.now()
    run_dir = RESULTS_DIR / f"{args.label}_{started:%Y%m%d_%H%M%S}"
    run_dir.mkdir(parents=True)
    print(f"Experiment '{args.label}': {len(task_paths)} task(s), "
          f"{llm.MODELS[args.provider]} via {args.provider}, reasoning {llm.REASONING_LEVEL}")

    results = []
    for i, task_path in enumerate(task_paths):
        if i > 0:
            time.sleep(WAIT_SECONDS)  # be gentle with the API rate limits
        print(f"\n[{i + 1}/{len(task_paths)}] {task_path.stem}")
        result = solve(task_path, args.provider, run_dir)
        print_result(result)
        results.append(result)

    solved = sum(r["correct"] for r in results)
    totals = {key: sum(r["tokens"][key] for r in results) for key in ("input", "reasoning", "answer")}
    print(f"\nSolved {solved}/{len(results)} ({solved / len(results):.0%})")
    print(f"Total tokens: input {totals['input']} | reasoning {totals['reasoning']} | answer {totals['answer']}")

    if from_file:
        summary = {
            "label": args.label,
            "tasks_file": args.tasks,
            "provider": args.provider,
            "model": llm.MODELS[args.provider],
            "reasoning_level": llm.REASONING_LEVEL,
            "started": started.isoformat(timespec="seconds"),
            "finished": datetime.now().isoformat(timespec="seconds"),
            "tasks": len(results),
            "solved": solved,
            "accuracy": round(solved / len(results), 3),
            "total_tokens": totals,
            "results": results,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Summary saved in {run_dir / 'summary.json'}")
    print(f"Results saved in {run_dir}")


if __name__ == "__main__":
    main()
