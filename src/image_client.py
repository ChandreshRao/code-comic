from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


DEFAULT_IMAGE_MODELS = ["black-forest-labs/FLUX.1-schnell", "gemini-2.5-flash-image"]


class ImageClient(ABC):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        raise NotImplementedError

    @classmethod
    def from_config(cls, config: Any) -> "ImageClient":
        models = getattr(config, "image_models_resolved", None) or DEFAULT_IMAGE_MODELS
        clients: list[ImageClient] = []
        for model in models:
            provider = cls._resolve_provider(config, model)
            client = cls._create_client(config, provider, model)
            if client is not None:
                clients.append(client)

        if len(clients) > 1:
            return ChainedImageClient(clients)
        if len(clients) == 1:
            return clients[0]
        return FallbackImageClient(getattr(config, "image_api_key", None), DEFAULT_IMAGE_MODELS[0])

    @staticmethod
    def _resolve_provider(config: Any, model: str) -> str:
        infer = getattr(config, "_infer_provider_from_model", None)
        if infer is not None:
            inferred = infer(model)
            if inferred:
                return inferred
        explicit = getattr(config, "image_provider", None)
        if explicit:
            return explicit.lower()
        return "huggingface"

    @staticmethod
    def _api_key_for_provider(config: Any, provider: str) -> str | None:
        if provider in ("gemini", "google"):
            return getattr(config, "gemini_api_key", None) or getattr(config, "image_api_key", None)
        if provider == "huggingface":
            return getattr(config, "hf_api_key", None) or getattr(config, "image_api_key", None)
        return getattr(config, "image_api_key", None)

    @classmethod
    def _create_client(cls, config: Any, provider: str, model: str) -> ImageClient | None:
        provider = provider.lower()
        api_key = cls._api_key_for_provider(config, provider)
        try:
            if provider == "openai":
                return OpenAIImageClient(api_key, model)
            if provider in ("gemini", "google"):
                return GeminiImageClient(api_key, model)
            if provider in ("huggingface", "hf", "stablediffusion"):
                return HuggingFaceImageClient(api_key, model)
        except Exception:
            return None
        return HuggingFaceImageClient(api_key, model)


class ChainedImageClient(ImageClient):
    def __init__(self, clients: list[ImageClient]) -> None:
        super().__init__(None, clients[0].model if clients else "")
        self._clients = clients

    def generate_image(self, prompt: str, output_path: Path) -> Path:
        errors: list[str] = []
        for client in self._clients:
            try:
                return client.generate_image(prompt, output_path)
            except RuntimeError as exc:
                errors.append(f"{client.__class__.__name__} ({client.model}): {exc}")
        raise RuntimeError("All image providers failed. " + "; ".join(errors))


class HuggingFaceImageClient(ImageClient):
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(token=self.api_key, model=self.model)
            image = client.text_to_image(prompt)
            image.save(output_path)
            return output_path
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Hugging Face image request failed: huggingface_hub is not installed. "
                "Install it with `pip install huggingface_hub` and try again."
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Hugging Face image creation failed: {exc}") from exc


class OpenAIImageClient(ImageClient):
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        try:
            import openai

            openai.api_key = self.api_key
            response = openai.Image.create(model=self.model, prompt=prompt, size="1024x1024")
            image_data = response.data[0].b64_json
            from base64 import b64decode

            output_path.write_bytes(b64decode(image_data))
            return output_path
        except Exception as exc:
            raise RuntimeError(f"OpenAI image creation failed: {exc}") from exc


class FallbackImageClient(ImageClient):
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        try:
            from PIL import Image, ImageDraw

            image = Image.new("RGB", (1024, 1024), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            message = "Placeholder image for comic panel"
            draw.text((50, 50), message, fill=(0, 0, 0))
            draw.text((50, 130), prompt[:500], fill=(0, 0, 0))
            image.save(output_path)
            return output_path
        except ImportError:
            fallback_path = output_path.with_suffix(".txt")
            fallback_path.write_text(
                f"Placeholder image for prompt:\n{prompt}\n\n" "Install Pillow to generate PNG fallback imagery.",
                encoding="utf-8",
            )
            return fallback_path


class GeminiImageClient(ImageClient):
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        if not self.api_key:
            raise RuntimeError(
                "Gemini image generation requires an API key. "
                "Set GEMINI_API_KEY or CODE_COMIC_IMAGE_API_KEY."
            )
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="1:1"),
                ),
            )
            for part in response.parts:
                if part.inline_data is not None:
                    part.as_image().save(output_path)
                    return output_path
            raise RuntimeError("Gemini returned no image data")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Gemini image request failed: google-genai is not installed. "
                "Install it with `pip install google-genai` and try again."
            ) from exc
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Gemini image creation failed: {exc}") from exc
