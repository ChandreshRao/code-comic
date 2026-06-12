from __future__ import annotations

import importlib
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
        provider = getattr(config, "llm_provider_resolved", None) or "openai"
        provider = provider.lower()
        model = getattr(config, "llm_model_default", "gemini")
        if provider == "openai":
            try:
                return OpenAIClient(config.llm_api_key, model)
            except Exception:
                return FallbackLLMClient(config.llm_api_key, model)
        if provider in ("gemini", "google"):
            # Check for the Google GenAI SDK or the legacy generativeai SDK.
            try:
                importlib.import_module("google.genai")
            except Exception:
                try:
                    importlib.import_module("google.generativeai")  # type: ignore
                except Exception:
                    return FallbackLLMClient(config.llm_api_key, model)
            try:
                return GeminiClient(config.llm_api_key, model)
            except Exception:
                return FallbackLLMClient(config.llm_api_key, model)
        # default fallback
        return FallbackLLMClient(config.llm_api_key, model)


class GeminiClient(LLMClient):
    def generate_text(self, prompt: str) -> str:
        try:
            try:
                importlib.invalidate_caches()
                import google.genai as genai  # type: ignore
            except Exception:
                try:
                    import google.generativeai as genai  # type: ignore
                except Exception as exc:
                    raise ModuleNotFoundError(
                        "Google Gemini SDK is not installed. "
                        "Install google-genai or google-generativeai and try again."
                    ) from exc

            if hasattr(genai, "Client"):
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                text = getattr(response, "text", None)
                if text is None and hasattr(response, "candidates"):
                    candidates = getattr(response, "candidates", [])
                    if candidates:
                        content = getattr(candidates[0], "content", None)
                        if content is not None:
                            text = getattr(content, "text", None)
                return (text or str(response)).strip()

            # Legacy google.generativeai adapter.
            genai.configure(api_key=self.api_key)
            response = genai.respond(model=self.model, prompt=prompt)
            return str(response).strip()
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Gemini LLM request failed: google.genai or google.generativeai is not installed. "
                "Install it with `pip install google-genai` and try again."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Gemini LLM request failed: {exc}") from exc


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
