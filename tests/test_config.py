from __future__ import annotations

import os

from src.config import Config


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
