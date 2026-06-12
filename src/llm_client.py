from __future__ import annotations

import importlib
from abc import ABC, abstractmethod
from typing import Any


DEFAULT_LLM_MODELS = ["gemini"]


class LLMClient(ABC):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError

    @classmethod
    def from_config(cls, config: Any) -> "LLMClient":
        models = getattr(config, "llm_models_resolved", None) or DEFAULT_LLM_MODELS
        clients: list[LLMClient] = []
        for model in models:
            provider = cls._resolve_provider(config, model)
            client = cls._create_client(config, provider, model)
            if client is not None:
                clients.append(client)

        if len(clients) > 1:
            return ChainedLLMClient(clients)
        if len(clients) == 1:
            return clients[0]
        return FallbackLLMClient(getattr(config, "llm_api_key", None), models[0])

    @staticmethod
    def _resolve_provider(config: Any, model: str) -> str:
        infer = getattr(config, "_infer_provider_from_model", None)
        if infer is not None:
            inferred = infer(model)
            if inferred:
                return inferred
        explicit = getattr(config, "llm_provider", None)
        if explicit:
            return explicit.lower()
        return "openai"

    @staticmethod
    def _api_key_for_provider(config: Any, provider: str) -> str | None:
        if provider in ("gemini", "google"):
            return getattr(config, "gemini_api_key", None) or getattr(config, "llm_api_key", None)
        if provider == "huggingface":
            return getattr(config, "hf_api_key", None) or getattr(config, "llm_api_key", None)
        return getattr(config, "llm_api_key", None)

    @classmethod
    def _create_client(cls, config: Any, provider: str, model: str) -> LLMClient | None:
        provider = provider.lower()
        api_key = cls._api_key_for_provider(config, provider)
        try:
            if provider == "openai":
                return OpenAIClient(api_key, model)
            if provider in ("gemini", "google"):
                try:
                    importlib.import_module("google.genai")
                except Exception:
                    try:
                        importlib.import_module("google.generativeai")  # type: ignore
                    except Exception:
                        return None
                return GeminiClient(api_key, model)
            if provider in ("huggingface", "hf"):
                return HuggingFaceLLMClient(api_key, model)
        except Exception:
            return None
        return None


class ChainedLLMClient(LLMClient):
    def __init__(self, clients: list[LLMClient]) -> None:
        super().__init__(None, clients[0].model if clients else "")
        self._clients = clients

    def generate_text(self, prompt: str) -> str:
        errors: list[str] = []
        for client in self._clients:
            try:
                return client.generate_text(prompt)
            except RuntimeError as exc:
                errors.append(f"{client.__class__.__name__} ({client.model}): {exc}")
        raise RuntimeError("All LLM providers failed. " + "; ".join(errors))


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


class HuggingFaceLLMClient(LLMClient):
    _SYSTEM_PROMPT = (
        "You are a helpful assistant that writes comic scene descriptions."
    )

    def generate_text(self, prompt: str) -> str:
        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(token=self.api_key, model=self.model)
            messages = [
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            try:
                response = client.chat_completion(
                    messages=messages,
                    max_tokens=700,
                )
                content = response.choices[0].message.content
                if content:
                    return content.strip()
            except Exception:
                pass

            generated = client.text_generation(
                prompt,
                max_new_tokens=700,
                return_full_text=False,
            )
            if isinstance(generated, list):
                text = generated[0].get("generated_text", "") if generated else ""
            else:
                text = str(generated)
            if not text.strip():
                raise RuntimeError("Hugging Face returned empty text")
            return text.strip()
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Hugging Face LLM request failed: huggingface_hub is not installed. "
                "Install it with `pip install huggingface_hub` and try again."
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Hugging Face LLM request failed: {exc}") from exc


class OpenAIClient(LLMClient):
    def generate_text(self, prompt: str) -> str:
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
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
