from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    output_dir: str
    llm_provider: str | None
    image_provider: str | None
    llm_models: list[str] | None
    image_models: list[str] | None
    llm_api_key: str | None
    image_api_key: str | None
    debug: bool = False

    @staticmethod
    def _parse_models(env_var: str | None) -> list[str] | None:
        if not env_var:
            return None
        parts = [p.strip() for p in env_var.split(",") if p.strip()]
        return parts or None

    @classmethod
    def from_env(
        cls,
        output_dir: str = "output",
        llm_provider: str | None = None,
        image_provider: str | None = None,
        debug: bool = False,
    ) -> "Config":
        # Read plural-only model env vars. Single-model env vars were removed by design.
        llm_models_env = os.environ.get("CODE_COMIC_LLM_MODELS")
        image_models_env = os.environ.get("CODE_COMIC_IMAGE_MODELS")

        llm_models = cls._parse_models(llm_models_env)
        image_models = cls._parse_models(image_models_env)

        return cls(
            output_dir=output_dir,
            llm_provider=llm_provider or os.environ.get("CODE_COMIC_LLM_PROVIDER"),
            image_provider=image_provider or os.environ.get("CODE_COMIC_IMAGE_PROVIDER"),
            llm_models=llm_models,
            image_models=image_models,
            llm_api_key=os.environ.get("CODE_COMIC_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            image_api_key=os.environ.get("CODE_COMIC_IMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            debug=debug,
        )

    @property
    def llm_model_default(self) -> str:
        if self.llm_models and len(self.llm_models) > 0:
            return self.llm_models[0]
        # default fallback LLM
        return "gemini"

    @property
    def image_model_default(self) -> str:
        if self.image_models and len(self.image_models) > 0:
            return self.image_models[0]
        # default fallback image model for free-tier preference
        return "gemini-2.5-flash-image"

    def _infer_provider_from_model(self, model: str) -> str | None:
        m = model.lower()
        if m.startswith("openai") or m.startswith("gpt"):
            return "openai"
        if "gemini" in m or m.startswith("google"):
            return "gemini"
        if m.startswith("stability") or "stable-diffusion" in m or "stablediffusion" in m:
            return "stablediffusion"
        if "github" in m:
            return "github"
        return None

    @property
    def llm_provider_resolved(self) -> str:
        if self.llm_provider:
            return self.llm_provider
        model = self.llm_model_default
        inferred = self._infer_provider_from_model(model)
        return inferred or "openai"

    @property
    def image_provider_resolved(self) -> str:
        if self.image_provider:
            return self.image_provider
        model = self.image_model_default
        inferred = self._infer_provider_from_model(model)
        return inferred or "openai"
