import os
from typing import List

import google.generativeai as genai
import requests
from anthropic import Anthropic
from openai import OpenAI

# --- Constants ---
DEFAULT_GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"),
    "gemini-3.0-pro-preview",
    "gemini-2.5-pro",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

DEFAULT_OPENAI_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]

DEFAULT_ANTHROPIC_MODELS = ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-4-8"]


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def _get_google_models(api_key: str) -> List[str]:
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                models.append(m.name.replace("models/", ""))
        return sorted(models) if models else []
    except Exception:
        return []


def _get_openai_models(api_key: str) -> List[str]:
    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        gpt_models = [m.id for m in models if m.id.startswith("gpt-") and "vision" not in m.id]
        return sorted(gpt_models) if gpt_models else []
    except Exception:
        return []


def _get_anthropic_models(api_key: str) -> List[str]:
    try:
        client = Anthropic(api_key=api_key)
        models = [m.id for m in client.models.list()]
        return models if models else []
    except Exception:
        return []


def _get_ollama_models() -> List[str]:
    """Lists models available on a local Ollama server. No API key required."""
    try:
        response = requests.get(f"{get_ollama_base_url()}/api/tags", timeout=5)
        response.raise_for_status()
        models = [m["name"] for m in response.json().get("models", [])]
        return sorted(models)
    except Exception:
        return []


def get_available_models(api_key: str, provider: str = "Google") -> List[str]:
    """
    Fetches available models for the specified AI provider.

    Args:
        api_key: The API key for the provider (unused for Ollama).
        provider: "Google", "OpenAI", "Anthropic", or "Ollama".

    Returns:
        A list of model IDs.
    """
    if provider == "Ollama":
        return _get_ollama_models()

    if not api_key:
        return []

    if provider == "Google":
        return _get_google_models(api_key)
    if provider == "OpenAI":
        return _get_openai_models(api_key)
    if provider == "Anthropic":
        return _get_anthropic_models(api_key)

    return []
