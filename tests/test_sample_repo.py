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

    config = Config.from_env(output_dir=str(tmp_path), debug=False, render_mode="html-image")
    renderer = ComicRenderer(config)
    result = renderer.render(str(sample_repo_path))

    image_files = [Path(p) for p in result["image_files"]]
    assert len(image_files) == 4
    assert all(path.suffix == ".png" for path in image_files)
    assert all(path.parent.name == "images" for path in image_files)
    assert all(path.exists() for path in image_files)
    assert all(path.stat().st_size > 0 for path in image_files)

    expected_html = tmp_path / "sample-repo-comic.html"
    assert result["html_file"] == str(expected_html)
    assert expected_html.exists()
    html_content = expected_html.read_text(encoding="utf-8")
    assert '<img src="images/panel-1.png"' in html_content

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

    config = Config.from_env(output_dir=str(tmp_path), debug=True, render_mode="html-image")
    if not config.llm_api_key:
        pytest.skip("GEMINI_API_KEY, CODE_COMIC_LLM_API_KEY, or OPENAI_API_KEY required for live test")
    if not config.image_api_key and not config.hf_api_key and not config.gemini_api_key:
        pytest.skip("HF_TOKEN, GEMINI_API_KEY, or CODE_COMIC_IMAGE_API_KEY required for live image test")

    renderer = ComicRenderer(config)
    result = renderer.render(str(sample_repo_path))

    if result.get("fallback") == "html-mermaid":
        pytest.skip(
            "Image API unavailable or model access denied; "
            "check HF_TOKEN and/or GEMINI_API_KEY for image model access"
        )

    assert result["render_mode_used"] == "html-image"
    image_files = [Path(p) for p in result["image_files"]]
    assert len(image_files) == 4
    assert all(path.suffix == ".png" for path in image_files)
    assert all(path.parent.name == "images" for path in image_files)
    assert all(path.exists() for path in image_files)
    assert all(path.stat().st_size > 0 for path in image_files)
