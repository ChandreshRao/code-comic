from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    output_dir: str
    llm_provider: str
    image_provider: str
    llm_model: str
    image_model: str
    llm_api_key: str | None
    image_api_key: str | None
    debug: bool = False

    @classmethod
    def from_env(
        cls,
        output_dir: str = "output",
        llm_provider: str | None = None,
        image_provider: str | None = None,
        llm_model: str | None = None,
        image_model: str | None = None,
        debug: bool = False,
    ) -> "Config":
        return cls(
            output_dir=output_dir,
            llm_provider=llm_provider or os.environ.get("CODE_COMIC_LLM_PROVIDER", "openai"),
            image_provider=image_provider or os.environ.get("CODE_COMIC_IMAGE_PROVIDER", "openai"),
            llm_model=llm_model or os.environ.get("CODE_COMIC_LLM_MODEL", "gpt-4o-mini"),
            image_model=image_model or os.environ.get("CODE_COMIC_IMAGE_MODEL", "gpt-image-1"),
            llm_api_key=os.environ.get("CODE_COMIC_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            image_api_key=os.environ.get("CODE_COMIC_IMAGE_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            debug=debug,
        )
