"""A very simple, educational ARC-AGI solver.

Usage:
    uv run solver/main.py ../data/training/<task>.json
    uv run solver/main.py ../data/training/<task>.json --provider openrouter
    uv run solver/main.py ../data/training/<task>.json --model gemini-flash-lite

The solver shows the model (Gemma 4 31B by default) the training examples and the test input(s),
asks it for the transformation rule and the predicted output grid(s), and
saves three files in outputs/<task>_<timestamp>/ (change it with --output-dir):

    prompt.txt   the exact prompt sent to the model
    log.txt      run information (provider, model, time, tokens, raw reply)
    answer.json  the rule summary and the predicted test output grid(s)
    reasoning.txt  how many reasoning (thinking) tokens the model used
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
# Each model has one name on the Google API and another on OpenRouter.
MODELS = {
    "gemma": {"google": "gemma-4-31b-it", "openrouter": "google/gemma-4-31b-it"},
    "gemini-flash-lite": {"google": "gemini-3.5-flash-lite", "openrouter": "google/gemini-3.5-flash-lite"},
}
REASONING_LEVEL = "high"


# ---------------------------------------------------------------------------
# 1. Build the prompt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 2. Call the model (two providers, same model)
# ---------------------------------------------------------------------------

def call_google(prompt, model):
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            # Gemma 4 thinking is on/off ("high" turns it on);
            # Gemini 3.5 Flash Lite defaults to "minimal", so "high" matters there.
            thinking_config=types.ThinkingConfig(thinking_level=REASONING_LEVEL),
        ),
    )
    usage = response.usage_metadata
    tokens = {
        "prompt": usage.prompt_token_count,
        "thinking": usage.thoughts_token_count,
        "output": usage.candidates_token_count,
    }
    return response.text or "", tokens


def call_openrouter(prompt, model):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning": {"effort": REASONING_LEVEL},
        },
        timeout=600,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage", {})
    tokens = {
        "prompt": usage.get("prompt_tokens"),
        "thinking": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "output": usage.get("completion_tokens"),
    }
    return data["choices"][0]["message"]["content"] or "", tokens


PROVIDERS = {
    "google": call_google,
    "openrouter": call_openrouter,
}


# ---------------------------------------------------------------------------
# 3. Read the answer out of the reply
# ---------------------------------------------------------------------------

def parse_answer(text):
    """Find the JSON object in the reply (models often wrap it in ```json fences)."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in the model reply")
    answer = json.loads(match.group(0))
    return {
        "rule_summary": answer.get("rule_summary", ""),
        "test_outputs": answer.get("test_outputs", []),
    }


# ---------------------------------------------------------------------------
# 4. Put it all together
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Solve an ARC-AGI task with Gemma 4 31B or Gemini 3.5 Flash Lite.")
    parser.add_argument("task", type=Path, help="path to the ARC task JSON, e.g. ../data/training/007bbfb7.json")
    parser.add_argument("--model", choices=MODELS, default="gemma")
    parser.add_argument("--provider", choices=PROVIDERS, default="google")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs", help="where to save the run folder (default: outputs/)")
    args = parser.parse_args()

    load_dotenv(find_dotenv())  # looks for .env here and in the parent folders
    task = json.loads(args.task.read_text(encoding="utf-8"))
    call_model = PROVIDERS[args.provider]
    model = MODELS[args.model][args.provider]

    run_dir = args.output_dir / f"{args.task.stem}_{datetime.now():%Y%m%d_%H%M%S}"
    run_dir.mkdir(parents=True)

    prompt = build_prompt(task)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    log = [
        f"task:            {args.task}",
        f"provider:        {args.provider}",
        f"model:           {model}",
        f"reasoning level: {REASONING_LEVEL}",
        f"started:         {datetime.now().isoformat(timespec='seconds')}",
    ]
    print(f"Asking {model} via {args.provider} (this can take a few minutes)...")

    start = time.time()
    reply, tokens = call_model(prompt, model)
    log += [f"duration:        {time.time() - start:.1f} s", f"tokens:          {tokens}"]

    try:
        answer = parse_answer(reply)
        log.append("parse:           ok")
    except ValueError as error:  # json.JSONDecodeError is a ValueError too
        answer = {"rule_summary": "", "test_outputs": [], "error": str(error)}
        log.append(f"parse:           FAILED ({error})")

    log += ["", "----- raw model reply -----", reply]
    (run_dir / "log.txt").write_text("\n".join(log), encoding="utf-8")
    (run_dir / "answer.json").write_text(json.dumps(answer, indent=2), encoding="utf-8")
    (run_dir / "reasoning.txt").write_text(
        f"reasoning tokens: {tokens['thinking']}\n"
        f"output tokens:    {tokens['output']}\n"
        f"prompt tokens:    {tokens['prompt']}\n",
        encoding="utf-8",
    )

    print(f"Rule: {answer['rule_summary'] or '(none)'}")
    print(f"Reasoning tokens: {tokens['thinking']}")
    print(f"Saved prompt, log, answer and reasoning in {run_dir}")
    print(f"Validate with: python -m uv run solver/validator.py {args.task} {run_dir / 'answer.json'}")


if __name__ == "__main__":
    main()
