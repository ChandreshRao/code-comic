from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ImageClient(ABC):
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        raise NotImplementedError

    @classmethod
    def from_config(cls, config: Any) -> "ImageClient":
        provider = getattr(config, "image_provider_resolved", None) or "openai"
        provider = provider.lower()
        model = getattr(config, "image_model_default", "gemini-2.5-flash-image")
        if provider == "openai":
            try:
                return OpenAIImageClient(config.image_api_key, model)
            except Exception:
                return FallbackImageClient(config.image_api_key, model)
        if provider in ("gemini", "google"):
            try:
                return GeminiImageClient(config.image_api_key, model)
            except Exception:
                return FallbackImageClient(config.image_api_key, model)
        return FallbackImageClient(config.image_api_key, model)


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
            from PIL import Image, ImageDraw, ImageFont

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
        # Placeholder adapter for Gemini image generation. If a Gemini image SDK
        # is available, replace this implementation to call it. For now, raise
        # a helpful error prompting installation/configuration.
        try:
            # Example: import google.generativeai as genai
            raise ImportError("No Gemini image SDK configured")
        except ImportError:
            raise RuntimeError(
                "Gemini image client is not available in this environment. "
                "Install or configure the appropriate SDK, or set a different image provider."
            )
