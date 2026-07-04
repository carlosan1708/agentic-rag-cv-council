"""Tests for the configuration service."""

from services.config_service import PROVIDERS, ConfigService


def test_providers_list():
    assert PROVIDERS == ["Google", "OpenAI", "Anthropic", "Ollama"]


def test_requires_api_key():
    assert ConfigService.requires_api_key("Google")
    assert ConfigService.requires_api_key("OpenAI")
    assert ConfigService.requires_api_key("Anthropic")
    assert not ConfigService.requires_api_key("Ollama")


def test_env_api_keys(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g-key")
    monkeypatch.setenv("OPENAI_API_KEY", "o-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a-key")
    assert ConfigService.get_env_api_key("Google") == "g-key"
    assert ConfigService.get_env_api_key("OpenAI") == "o-key"
    assert ConfigService.get_env_api_key("Anthropic") == "a-key"
    assert ConfigService.get_env_api_key("Ollama") == ""


def test_is_online(monkeypatch):
    monkeypatch.setenv("ONLINE_MODE", "true")
    assert ConfigService.get_is_online()
    monkeypatch.setenv("ONLINE_MODE", "false")
    assert not ConfigService.get_is_online()


def test_cheap_models_exist_for_key_providers():
    for provider in ("Google", "OpenAI", "Anthropic"):
        assert ConfigService.get_cheap_model(provider)


def test_fetch_models_without_key_returns_empty():
    assert ConfigService.fetch_models("Google", "") == []


def test_fetch_models_system_key_uses_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "system-key")
    models = ConfigService.fetch_models("Anthropic", "system-key")
    assert "claude-haiku-4-5" in models
