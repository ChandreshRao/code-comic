from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.analyzer import analyze_repository
from src.config import Config
from src.image_client import FallbackImageClient
from src.renderer import ComicRenderer
from tests.test_renderer import FakeLLMClient


def test_analyze_sample_repo(sample_repo_path: Path) -> None:
    metadata = analyze_repository(str(sample_repo_path))

    assert metadata["total_files"] >= 5
    assert "README.md" in metadata["top_level"]
    assert "src" in metadata["top_level"]
    assert "py" in metadata["languages"]
    assert "pyproject.toml" in metadata["package_files"]
    assert "README" in metadata["detected_features"]
    assert metadata["files_analyzed"] >= 1
    assert any("readme" in name.lower() for name in metadata.get("content", {}))


def test_renderer_generates_png_panels_from_sample_repo(
    sample_repo_path: Path, tmp_path: Path, monkeypatch
) -> None:
    """End-to-end smoke test: real repo analysis + placeholder PNG panels (no API keys)."""
    fake_llm = FakeLLMClient()

    monkeypatch.setattr("src.renderer.LLMClient.from_config", lambda config: fake_llm)
    monkeypatch.setattr(
        "src.renderer.ImageClient.from_config",
        lambda config: FallbackImageClient(None, "fallback"),
    )

    config = Config.from_env(output_dir=str(tmp_path), debug=False, render_mode="image")
    renderer = ComicRenderer(config)
    result = renderer.render(str(sample_repo_path))

    image_files = [Path(p) for p in result["image_files"]]
    assert len(image_files) == 4
    assert all(path.suffix == ".png" for path in image_files)
    assert all(path.exists() for path in image_files)
    assert all(path.stat().st_size > 0 for path in image_files)

    metadata_path = tmp_path / "repo_metadata.json"
    assert metadata_path.exists()
    assert result["metadata"]["path"].endswith("sample-repo")


@pytest.mark.integration
def test_live_image_generation_from_sample_repo(
    sample_repo_path: Path, tmp_path: Path, monkeypatch
) -> None:
    """Optional live test: calls real LLM and image APIs when CODE_COMIC_RUN_LIVE=1."""
    if os.environ.get("CODE_COMIC_RUN_LIVE") != "1":
        pytest.skip("Set CODE_COMIC_RUN_LIVE=1 to run live image generation test")

    config = Config.from_env(output_dir=str(tmp_path), debug=True)
    if not config.llm_api_key:
        pytest.skip("GEMINI_API_KEY, CODE_COMIC_LLM_API_KEY, or OPENAI_API_KEY required for live test")

    renderer = ComicRenderer(config)
    result = renderer.render(str(sample_repo_path), generate_images=True)

    image_files = [Path(p) for p in result["image_files"]]
    assert len(image_files) == 4
    assert all(path.exists() for path in image_files)
    assert all(path.stat().st_size > 0 for path in image_files)
