from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError

    @classmethod
    def from_config(cls, config: Any) -> "LLMClient":
        provider = config.llm_provider.lower()
        if provider == "openai":
            try:
                from openai import OpenAI

                return OpenAIClient(config.llm_api_key, config.llm_model)
            except ImportError:
                return FallbackLLMClient(config.llm_api_key, config.llm_model)
        return FallbackLLMClient(config.llm_api_key, config.llm_model)


class OpenAIClient(LLMClient):
    def generate_text(self, prompt: str) -> str:
        try:
            import openai

            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes comic scene descriptions."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=700,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            raise RuntimeError(f"OpenAI LLM request failed: {exc}") from exc


class FallbackLLMClient(LLMClient):
    def generate_text(self, prompt: str) -> str:
        return (
            "[Fallback LLM] Could not load a provider-specific library or API key. "
            "Use a real LLM provider for richer output."
        )
