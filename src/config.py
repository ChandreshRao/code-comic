from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .image_client import DEFAULT_IMAGE_MODELS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_dotenv_loaded = False


def _ensure_dotenv_loaded() -> None:
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    load_dotenv(_PROJECT_ROOT / ".env")
    load_dotenv()
    _dotenv_loaded = True


# Try to import tomllib (Python 3.11+) or tomli as fallback
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore


@dataclass
class Config:
    output_dir: str
    llm_provider: str | None
    image_provider: str | None
    llm_models: list[str] | None
    image_models: list[str] | None
    llm_api_key: str | None
    image_api_key: str | None
    hf_api_key: str | None = None
    gemini_api_key: str | None = None
    context_mode: str = "lightweight"  # "lightweight" or "comprehensive"
    render_mode: str = "image"  # "image", "html", or "text"
    max_content_size_bytes: int = 500_000  # 500KB threshold for warnings
    ignore_patterns: list[str] | None = None  # Additional patterns to ignore
    debug: bool = False

    @staticmethod
    def _parse_models(env_var: str | None) -> list[str] | None:
        if not env_var:
            return None
        parts = [p.strip() for p in env_var.split(",") if p.strip()]
        return parts or None

    @staticmethod
    def _parse_ignore_patterns(env_var: str | None) -> list[str] | None:
        if not env_var:
            return None
        parts = [p.strip() for p in env_var.split(",") if p.strip()]
        return parts or None

    @staticmethod
    def _load_pyproject_config(
        repo_root: Path | str | None = None,
    ) -> dict:
        """
        Load code-comic config from pyproject.toml [tool.code-comic] section.

        Returns:
            Dict with config keys (empty dict if not found)
        """
        if tomllib is None:
            return {}

        if repo_root is None:
            repo_root = Path.cwd()
        else:
            repo_root = Path(repo_root)

        pyproject_path = repo_root / "pyproject.toml"
        if not pyproject_path.exists():
            return {}

        try:
            # Python 3.11+ uses binary mode for tomllib
            mode = "rb" if hasattr(tomllib, "loads") else "r"
            with open(pyproject_path, mode) as f:
                data = tomllib.load(f) if mode == "rb" else tomllib.loads(f.read())
            return data.get("tool", {}).get("code-comic", {})
        except (OSError, Exception):
            return {}

    @classmethod
    def from_env(
        cls,
        output_dir: str = "output",
        llm_provider: str | None = None,
        image_provider: str | None = None,
        debug: bool = False,
        context_mode: str = "lightweight",
        render_mode: str = "image",
        repo_root: Path | str | None = None,
    ) -> "Config":
        _ensure_dotenv_loaded()

        # Load config from pyproject.toml [tool.code-comic] section
        # Precedence: CLI args > env vars > pyproject.toml > defaults
        pyproject_config = cls._load_pyproject_config(repo_root)

        # Read plural-only model env vars. Single-model env vars were removed by design.
        llm_models_env = os.environ.get("CODE_COMIC_LLM_MODELS")
        image_models_env = os.environ.get("CODE_COMIC_IMAGE_MODELS")

        llm_models = cls._parse_models(llm_models_env)
        image_models = cls._parse_models(image_models_env)

        # Parse context mode (env > pyproject.toml > default)
        env_context_mode = os.environ.get("CODE_COMIC_CONTEXT_MODE")
        pyproject_context_mode = pyproject_config.get("context-mode") or pyproject_config.get("context_mode")
        final_context_mode = env_context_mode or pyproject_context_mode or context_mode

        # Parse render mode (CLI > env > pyproject.toml > default)
        env_render_mode = os.environ.get("CODE_COMIC_RENDER_MODE")
        pyproject_render_mode = pyproject_config.get("render-mode") or pyproject_config.get("render_mode")
        final_render_mode = env_render_mode or pyproject_render_mode or render_mode

        # Parse ignore patterns (env > pyproject.toml > default)
        env_ignore_patterns = os.environ.get("CODE_COMIC_IGNORE_PATTERNS")
        pyproject_ignore_patterns = pyproject_config.get("ignore-patterns") or pyproject_config.get("ignore_patterns")
        ignore_patterns = None
        if env_ignore_patterns:
            ignore_patterns = cls._parse_ignore_patterns(env_ignore_patterns)
        elif pyproject_ignore_patterns:
            if isinstance(pyproject_ignore_patterns, list):
                ignore_patterns = pyproject_ignore_patterns
            elif isinstance(pyproject_ignore_patterns, str):
                ignore_patterns = cls._parse_ignore_patterns(pyproject_ignore_patterns)

        # Parse max content size from env/pyproject (in KB for convenience, stored as bytes)
        max_content_size_str = (
            os.environ.get("CODE_COMIC_MAX_CONTENT_SIZE")
            or str(pyproject_config.get("max-content-size-kb") or pyproject_config.get("max_content_size_kb") or "")
        )
        max_content_size_bytes = 500_000  # Default 500KB
        if max_content_size_str:
            try:
                max_content_size_bytes = int(max_content_size_str) * 1024  # Convert KB to bytes
            except ValueError:
                pass

        hf_api_key = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_API_KEY")
            or os.environ.get("CODE_COMIC_HF_API_KEY")
        )
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        image_api_key = (
            os.environ.get("CODE_COMIC_IMAGE_API_KEY")
            or hf_api_key
            or gemini_api_key
            or os.environ.get("OPENAI_API_KEY")
        )

        return cls(
            output_dir=output_dir,
            llm_provider=llm_provider or os.environ.get("CODE_COMIC_LLM_PROVIDER"),
            image_provider=image_provider or os.environ.get("CODE_COMIC_IMAGE_PROVIDER"),
            llm_models=llm_models,
            image_models=image_models,
            llm_api_key=os.environ.get("CODE_COMIC_LLM_API_KEY") or gemini_api_key or os.environ.get("OPENAI_API_KEY"),
            image_api_key=image_api_key,
            hf_api_key=hf_api_key,
            gemini_api_key=gemini_api_key,
            context_mode=final_context_mode,
            render_mode=final_render_mode,
            max_content_size_bytes=max_content_size_bytes,
            ignore_patterns=ignore_patterns,
            debug=debug,
        )

    @property
    def llm_model_default(self) -> str:
        if self.llm_models and len(self.llm_models) > 0:
            return self.llm_models[0]
        # default fallback LLM
        return "gemini"

    @property
    def image_models_resolved(self) -> list[str]:
        if self.image_models and len(self.image_models) > 0:
            return self.image_models
        return list(DEFAULT_IMAGE_MODELS)

    @property
    def image_model_default(self) -> str:
        return self.image_models_resolved[0]

    def _infer_provider_from_model(self, model: str) -> str | None:
        m = model.lower()
        if m.startswith("openai") or m.startswith("gpt"):
            return "openai"
        if "gemini" in m or m.startswith("google"):
            return "gemini"
        if m.startswith("stability") or "stable-diffusion" in m or "stablediffusion" in m:
            return "huggingface"
        if "github" in m:
            return "github"
        if "/" in m:
            return "huggingface"
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
        return inferred or "huggingface"
