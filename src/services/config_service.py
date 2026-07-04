import os
from typing import List

from exceptions import LLMProviderError
from llm_utils import (
    DEFAULT_ANTHROPIC_MODELS,
    DEFAULT_GEMINI_MODELS,
    DEFAULT_OPENAI_MODELS,
    get_available_models,
)
from logger import logger

PROVIDERS = ["Google", "OpenAI", "Anthropic", "Ollama"]

# Providers that do not require an API key
KEYLESS_PROVIDERS = {"Ollama"}

CHEAP_MODELS = {
    "Google": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"),
    "OpenAI": "gpt-4o-mini",
    "Anthropic": "claude-haiku-4-5",
    "Ollama": "",
}

ENV_KEY_NAMES = {
    "Google": "GOOGLE_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Anthropic": "ANTHROPIC_API_KEY",
}

DEFAULT_MODELS = {
    "Google": DEFAULT_GEMINI_MODELS,
    "OpenAI": DEFAULT_OPENAI_MODELS,
    "Anthropic": DEFAULT_ANTHROPIC_MODELS,
}


class ConfigService:
    @staticmethod
    def get_is_online() -> bool:
        return os.getenv("ONLINE_MODE", "false").lower() == "true"

    @staticmethod
    def requires_api_key(provider: str) -> bool:
        return provider not in KEYLESS_PROVIDERS

    @staticmethod
    def get_env_api_key(provider: str) -> str:
        env_name = ENV_KEY_NAMES.get(provider)
        return os.getenv(env_name, "") if env_name else ""

    @staticmethod
    def fetch_models(provider: str, api_key: str) -> List[str]:
        if ConfigService.requires_api_key(provider) and not api_key:
            logger.warning(f"Attempted to fetch models for {provider} without an API key.")
            return []

        # Use defaults if using system key
        system_key = ConfigService.get_env_api_key(provider)
        if api_key and api_key == system_key and provider in DEFAULT_MODELS:
            logger.info(f"Using system default models for {provider}.")
            return DEFAULT_MODELS[provider]

        try:
            logger.info(f"Fetching available models for {provider}...")
            models = get_available_models(api_key, provider)
            logger.info(f"Successfully fetched {len(models)} models for {provider}.")
            return models
        except Exception as e:
            logger.error(f"Failed to fetch models for {provider}: {str(e)}")
            raise LLMProviderError(f"Could not retrieve models from {provider}. Please check your API key.") from e

    @staticmethod
    def get_cheap_model(provider: str) -> str:
        return CHEAP_MODELS.get(provider, "")
