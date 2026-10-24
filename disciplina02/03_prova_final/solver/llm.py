"""Talking to the LLM. Both providers run the same model and return the same thing:
the reply text and a dict with the input, reasoning and output token counts."""

import os
import time

import requests
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.5-flash-lite"
# Gemini 3.5 Flash Lite thinks at "minimal" level by default; the project asks for "high".
DEFAULT_REASONING = "high"
REASONING_LEVELS = ("minimal", "low", "medium", "high")
# Rate limits and overloaded servers are temporary: try again a few times before giving up.
RETRIES = 3
RETRY_WAIT_SECONDS = 20


def model_name(model, provider):
    """The same model has one name on the Google API and another on OpenRouter."""
    if provider == "openrouter" and "/" not in model:
        return f"google/{model}"
    return model


def call_google(prompt, model, reasoning):
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=reasoning),
        ),
    )
    usage = response.usage_metadata
    tokens = {
        "input": usage.prompt_token_count or 0,
        "reasoning": usage.thoughts_token_count or 0,
        "output": usage.candidates_token_count or 0,
    }
    return response.text or "", tokens


def call_openrouter(prompt, model, reasoning):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "reasoning": {"effort": reasoning},
        },
        timeout=600,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage", {})
    # OpenRouter counts reasoning inside completion_tokens, so we subtract it.
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    tokens = {
        "input": usage.get("prompt_tokens") or 0,
        "reasoning": reasoning_tokens,
        "output": (usage.get("completion_tokens") or 0) - reasoning_tokens,
    }
    return data["choices"][0]["message"]["content"] or "", tokens


PROVIDERS = {
    "google": call_google,
    "openrouter": call_openrouter,
}


def is_temporary(error):
    """429 (rate limit) and 5xx (server busy) are worth retrying; anything else is not."""
    text = str(error)
    return any(code in text for code in ("429", "500", "502", "503", "504", "RESOURCE_EXHAUSTED", "UNAVAILABLE"))


def ask(prompt, provider="google", model=DEFAULT_MODEL, reasoning=DEFAULT_REASONING):
    """Send the prompt to the model through the chosen provider."""
    for attempt in range(1, RETRIES + 1):
        try:
            return PROVIDERS[provider](prompt, model_name(model, provider), reasoning)
        except Exception as error:
            if attempt == RETRIES or not is_temporary(error):
                raise
            print(f"  temporary API error ({type(error).__name__}), retrying in {RETRY_WAIT_SECONDS} s...")
            time.sleep(RETRY_WAIT_SECONDS)
