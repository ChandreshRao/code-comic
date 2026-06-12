from __future__ import annotations

import os

import pytest

from src.config import Config


@pytest.fixture(autouse=True)
def _isolate_from_local_dotenv(monkeypatch) -> None:
    """Prevent the developer's .env from affecting config unit tests."""
    monkeypatch.setattr("src.config._dotenv_loaded", True)


def test_config_from_env_parses_plural_model_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("CODE_COMIC_LLM_MODELS", "gemini,openai/gpt-4o-mini")
    monkeypatch.setenv("CODE_COMIC_IMAGE_MODELS", "gemini-2.5-flash-image,stability-ai/stable-diffusion")
    monkeypatch.delenv("CODE_COMIC_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("CODE_COMIC_IMAGE_PROVIDER", raising=False)

    config = Config.from_env(output_dir="output", debug=False)

    assert config.llm_models == ["gemini", "openai/gpt-4o-mini"]
    assert config.image_models == ["gemini-2.5-flash-image", "stability-ai/stable-diffusion"]
    assert config.llm_model_default == "gemini"
    assert config.image_model_default == "gemini-2.5-flash-image"
    assert config.llm_provider_resolved == "gemini"
    assert config.image_provider_resolved == "gemini"


def test_config_from_env_reads_gemini_api_key(monkeypatch) -> None:
    monkeypatch.delenv("CODE_COMIC_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CODE_COMIC_IMAGE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    config = Config.from_env(output_dir="output", debug=False)

    assert config.llm_api_key == "test-gemini-key"
    assert config.image_api_key == "test-gemini-key"


def test_config_from_env_reads_render_mode(monkeypatch) -> None:
    monkeypatch.setenv("CODE_COMIC_RENDER_MODE", "html")

    config = Config.from_env(output_dir="output", debug=False)

    assert config.render_mode == "html"

