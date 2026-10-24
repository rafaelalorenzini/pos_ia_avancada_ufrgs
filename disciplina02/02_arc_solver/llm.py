"""Talking to the LLM. Both providers run the same model and return the same thing:
the reply text and a dict with the input, reasoning and answer token counts."""

import os

import requests
from google import genai
from google.genai import types

# The same model has one name on the Google API and another on OpenRouter.
MODELS = {
    "google": "gemini-3.5-flash-lite",
    "openrouter": "google/gemini-3.5-flash-lite",
}
# Gemini 3.5 Flash Lite thinks at "minimal" level by default; ARC needs more.
REASONING_LEVEL = "high"


def call_google(prompt, model):
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=REASONING_LEVEL),
        ),
    )
    usage = response.usage_metadata
    tokens = {
        "input": usage.prompt_token_count or 0,
        "reasoning": usage.thoughts_token_count or 0,
        "answer": usage.candidates_token_count or 0,
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
    # OpenRouter counts reasoning inside completion_tokens, so we subtract it.
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    tokens = {
        "input": usage.get("prompt_tokens") or 0,
        "reasoning": reasoning,
        "answer": (usage.get("completion_tokens") or 0) - reasoning,
    }
    return data["choices"][0]["message"]["content"] or "", tokens


PROVIDERS = {
    "google": call_google,
    "openrouter": call_openrouter,
}


def ask(prompt, provider="google"):
    """Send the prompt to the model through the chosen provider."""
    return PROVIDERS[provider](prompt, MODELS[provider])
