"""ARC-AGI-1 solver with two approaches, both using Gemini 3.5 Flash Lite with high reasoning.

    end to end (direct)      the model writes the output grid(s) directly
    code generation (code)   the model writes transform(grid); we run it, with a time limit,
                             on the training examples and on the test input(s)

Usage (run from the project folder, the one with tarefas/ and solver/):
    uv run solver/main.py                                   # the 20 tasks of tarefas/tarefas.txt, both approaches
    uv run solver/main.py --approach direct                 # only end to end
    uv run solver/main.py --approach code                   # only code generation
    uv run solver/main.py --only 3aa6fb7a 44d8ac46          # just some tasks of the list (quick tests)
    uv run solver/main.py tarefas/training/0a938d79.json --model gemini-3.5-flash-lite --reasoning high
    uv run solver/main.py --provider openrouter --label test

Everything is saved in resultados/<label>_<timestamp>/:
    <approach>/<task_id>/prompt.txt     the exact prompt sent to the model
    <approach>/<task_id>/response.txt   the raw reply of the model
    <approach>/<task_id>/answer.json    predictions (and code), tokens, time, correct or not
    <approach>/<task_id>/transform.py   the generated program (code generation only)
    summary_<approach>.json             totals and the result of each task
    summary_<approach>.csv              one line per task, handy for the report table
"""

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

import llm
from prompt import build_code_prompt, build_direct_prompt, extract_code, parse_direct_answer
from sandbox import TIMEOUT_SECONDS, run_transform
from validator import is_grid, validate

ROOT = Path(__file__).resolve().parent
DEFAULT_TASKS = ROOT.parent / "tarefas" / "tarefas.txt"
RESULTS_DIR = ROOT.parent / "resultados"
WAIT_SECONDS = 2  # pause between two tasks (the project asks for at least 1 s between API calls)
APPROACHES = {"direct": "end to end", "code": "code generation"}
TOKEN_KINDS = ("input", "reasoning", "output")


# ---------------------------------------------------------------------------
# Finding the tasks
# ---------------------------------------------------------------------------

def read_task_list(tasks_file):
    """One task path per line, relative to the list itself; blank lines and # comments are ignored."""
    tasks_file = Path(tasks_file)
    lines = tasks_file.read_text(encoding="utf-8").splitlines()
    entries = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    paths = []
    for entry in entries:
        path = Path(entry) if Path(entry).is_absolute() else tasks_file.parent / entry
        if not path.is_file():
            raise FileNotFoundError(f"task not found: {entry} (listed in {tasks_file})")
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Solving one task, end to end
# ---------------------------------------------------------------------------

def new_result(task_path):
    return {
        "task_id": task_path.stem,
        "set": task_path.parent.name,  # training or evaluation
        "correct": False,
        "tests_correct": [],
        "tokens": {kind: 0 for kind in TOKEN_KINDS},
        "seconds": 0.0,
        "error": None,
    }


def solve_direct(task, task_path, llm_config, task_dir):
    prompt = build_direct_prompt(task)
    (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    result = new_result(task_path)
    answer = {"rule_summary": "", "test_outputs": []}
    start = time.time()
    try:
        reply, result["tokens"] = llm.ask(prompt, **llm_config)
        (task_dir / "response.txt").write_text(reply, encoding="utf-8")
        answer = parse_direct_answer(reply)
        result["tests_correct"] = validate(task, answer["test_outputs"])
        result["correct"] = all(result["tests_correct"])
    except Exception as error:  # keep going: one bad task should not stop an experiment
        result["error"] = f"{type(error).__name__}: {error}"
    result["seconds"] = round(time.time() - start, 1)

    (task_dir / "answer.json").write_text(json.dumps({**answer, **result}, indent=2), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Solving one task, by code generation
# ---------------------------------------------------------------------------

def solve_code(task, task_path, llm_config, task_dir):
    prompt = build_code_prompt(task)
    (task_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    result = new_result(task_path)
    result.update({"train_correct": [], "train_all_correct": False, "run_errors": []})
    test_outputs = []
    start = time.time()
    try:
        reply, result["tokens"] = llm.ask(prompt, **llm_config)
        (task_dir / "response.txt").write_text(reply, encoding="utf-8")
        code = extract_code(reply)
        (task_dir / "transform.py").write_text(code + "\n", encoding="utf-8")

        # Training examples: does the program reproduce every known output?
        for i, pair in enumerate(task["train"], start=1):
            output, error = run_transform(code, pair["input"])
            if error:
                result["run_errors"].append(f"train {i}: {error}")
            result["train_correct"].append(is_grid(output) and output == pair["output"])
        result["train_all_correct"] = all(result["train_correct"])

        # Test inputs: the program's outputs are the answer, whatever happened on training.
        for i, pair in enumerate(task["test"], start=1):
            output, error = run_transform(code, pair["input"])
            if error:
                result["run_errors"].append(f"test {i}: {error}")
            test_outputs.append(output)
        result["tests_correct"] = validate(task, test_outputs)
        result["correct"] = all(result["tests_correct"])
    except Exception as error:  # keep going: one bad task should not stop an experiment
        result["error"] = f"{type(error).__name__}: {error}"
    result["seconds"] = round(time.time() - start, 1)

    (task_dir / "answer.json").write_text(json.dumps({"test_outputs": test_outputs, **result}, indent=2),
                                          encoding="utf-8")
    return result


SOLVERS = {"direct": solve_direct, "code": solve_code}


def print_result(result):
    t = result["tokens"]
    print(f"  tokens: input {t['input']} | reasoning {t['reasoning']} | output {t['output']}")
    if "train_correct" in result and result["train_correct"]:
        train = result["train_correct"]
        print(f"  train:  {sum(train)}/{len(train)} examples correct")
    for run_error in result.get("run_errors", []):
        print(f"  run error: {run_error}")
    if result["error"]:
        print(f"  result: ERROR ({result['error']}, {result['seconds']} s)")
    else:
        tests = result["tests_correct"]
        verdict = "SOLVED" if result["correct"] else "NOT SOLVED"
        print(f"  result: {verdict} ({sum(tests)}/{len(tests)} test outputs correct, {result['seconds']} s)")


# ---------------------------------------------------------------------------
# Running one approach over all tasks, and saving its summary
# ---------------------------------------------------------------------------

def run_approach(approach, task_paths, llm_config, run_dir):
    print(f"\n=== {APPROACHES[approach]} ({approach}) ===")
    started = datetime.now()
    wall_start = time.time()
    results = []
    for i, task_path in enumerate(task_paths):
        if i > 0:
            time.sleep(WAIT_SECONDS)  # be gentle with the API rate limits
        print(f"\n[{i + 1}/{len(task_paths)}] {task_path.stem} ({task_path.parent.name})")
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task_dir = run_dir / approach / task_path.stem
        task_dir.mkdir(parents=True)
        result = SOLVERS[approach](task, task_path, llm_config, task_dir)
        print_result(result)
        results.append(result)

    summary = {
        "approach": approach,
        "approach_name": APPROACHES[approach],
        "provider": llm_config["provider"],
        "model": llm_config["model"],
        "reasoning_level": llm_config["reasoning"],
        "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now().isoformat(timespec="seconds"),
        "tasks": len(results),
        "solved": sum(r["correct"] for r in results),
        "errors": sum(r["error"] is not None for r in results),
        "total_tokens": {kind: sum(r["tokens"][kind] for r in results) for kind in TOKEN_KINDS},
        # time spent solving (API calls + running the code), without the pauses between calls
        "total_seconds": round(sum(r["seconds"] for r in results), 1),
        "wall_clock_seconds": round(time.time() - wall_start, 1),
    }
    if approach == "code":
        summary["train_all_correct"] = sum(r["train_all_correct"] for r in results)
        summary["train_correct_but_test_wrong"] = sum(r["train_all_correct"] and not r["correct"] for r in results)
        summary["timeout_seconds"] = TIMEOUT_SECONDS
    summary["results"] = results

    (run_dir / f"summary_{approach}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    save_csv(run_dir / f"summary_{approach}.csv", approach, results)
    print_summary(summary)
    return summary


def save_csv(path, approach, results):
    columns = ["task_id", "set", "correct", "input_tokens", "reasoning_tokens", "output_tokens", "seconds"]
    if approach == "code":
        columns.insert(3, "train_all_correct")
    columns.append("error")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow({**r, **{f"{kind}_tokens": r["tokens"][kind] for kind in TOKEN_KINDS}})


def print_summary(summary):
    t = summary["total_tokens"]
    print(f"\n--- {summary['approach_name']} ---")
    print(f"Solved: {summary['solved']}/{summary['tasks']}")
    if "train_all_correct" in summary:
        print(f"Program correct on all training examples: {summary['train_all_correct']}/{summary['tasks']}")
    print(f"Tokens: input {t['input']} | reasoning {t['reasoning']} | output {t['output']}")
    print(f"Time: {summary['total_seconds']} s solving ({summary['wall_clock_seconds']} s with pauses)")


def main():
    parser = argparse.ArgumentParser(description="Solve ARC-AGI-1 tasks end to end and by code generation.")
    parser.add_argument("tasks", nargs="?", default=str(DEFAULT_TASKS),
                        help="a .txt file listing task JSON paths (default: tarefas/tarefas.txt) or one task JSON")
    parser.add_argument("--approach", choices=["both", *APPROACHES], default="both")
    parser.add_argument("--only", nargs="+", metavar="TASK_ID", help="solve only these task ids from the list")
    parser.add_argument("--provider", choices=llm.PROVIDERS, default="google")
    parser.add_argument("--model", default=llm.DEFAULT_MODEL, help=f"default: {llm.DEFAULT_MODEL}")
    parser.add_argument("--reasoning", choices=llm.REASONING_LEVELS, default=llm.DEFAULT_REASONING,
                        help=f"reasoning level (default: {llm.DEFAULT_REASONING})")
    parser.add_argument("--label", default="experiment", help="a name for this experiment")
    args = parser.parse_args()

    load_dotenv(find_dotenv(usecwd=True))  # looks for .env here and in the parent folders
    load_dotenv(ROOT.parent / ".env")  # and in the project folder, wherever we are run from

    task_paths = read_task_list(args.tasks) if args.tasks.endswith(".txt") else [Path(args.tasks)]
    if args.only:
        task_paths = [p for p in task_paths if p.stem in args.only]
        if not task_paths:
            raise SystemExit(f"none of {args.only} is in {args.tasks}")
    approaches = list(APPROACHES) if args.approach == "both" else [args.approach]
    llm_config = {"provider": args.provider, "model": args.model, "reasoning": args.reasoning}

    run_dir = RESULTS_DIR / f"{args.label}_{datetime.now():%Y%m%d_%H%M%S}"
    run_dir.mkdir(parents=True)
    print(f"Experiment '{args.label}': {len(task_paths)} task(s), {', '.join(approaches)}, "
          f"{args.model} via {args.provider}, reasoning {args.reasoning}")

    summaries = []
    for i, approach in enumerate(approaches):
        if i > 0:
            time.sleep(WAIT_SECONDS)
        summaries.append(run_approach(approach, task_paths, llm_config, run_dir))

    if len(summaries) > 1:
        print("\n=== Comparison ===")
        for s in summaries:
            t = s["total_tokens"]
            extra = f" | train all correct {s['train_all_correct']}" if "train_all_correct" in s else ""
            print(f"{s['approach_name']:>16}: solved {s['solved']}/{s['tasks']} | tokens in {t['input']} "
                  f"reasoning {t['reasoning']} out {t['output']} | {s['total_seconds']} s{extra}")
    print(f"\nResults saved in {run_dir}")


if __name__ == "__main__":
    main()
