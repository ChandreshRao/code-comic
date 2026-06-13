from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from src.config import Config
from src.html_renderer import render_comic_html
from src.prompt_generator import _build_fallback_mermaid, build_scene_prompt
from src.renderer import ComicRenderer


class FakeLLMClient:
    def generate_text(self, prompt: str) -> str:
        return (
            '[{"title": "Welcome to the Repo", "description": "Intro.", "panel_text": "First prompt text.", '
            '"speech_bubble": "Hello repo!", "mermaid": "flowchart TD\\n    A --> B"}, '
            '{"title": "Follow the Flow", "description": "Build.", "panel_text": "Second prompt text.", '
            '"speech_bubble": "Build it!", "mermaid": "flowchart TD\\n    B --> C"}, '
            '{"title": "Core Logic", "description": "Review.", "panel_text": "Third prompt text.", '
            '"speech_bubble": "Review time.", "mermaid": "flowchart TD\\n    C --> D"}, '
            '{"title": "Ship It", "description": "Ship.", "panel_text": "Fourth prompt text.", '
            '"speech_bubble": "Ship it!", "mermaid": "flowchart TD\\n    D --> E"}]'
        )


class FakeImageClient:
    def __init__(self) -> None:
        self.generated: list[Dict[str, Any]] = []

    def generate_image(self, prompt: str, output_path: Path) -> Path:
        output_path.write_text(f"IMAGE GENERATED FROM: {prompt}", encoding="utf-8")
        self.generated.append({"prompt": prompt, "path": output_path})
        return output_path


class FailingImageClient:
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        raise RuntimeError(
            "Gemini image client is not available in this environment. "
            "Install or configure the appropriate SDK, or set a different image provider."
        )


def test_renderer_html_image_saves_images_and_html(tmp_path: Path, monkeypatch) -> None:
    metadata = {
        "path": str(tmp_path),
        "top_level": ["src", "README.md"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "total_files": 2,
        "context_mode": "lightweight",
        "content_warnings": [],
        "files_analyzed": 0,
    }

    def fake_analyze_repository(
        repo_path: str,
        context_mode: str = "lightweight",
        custom_ignore_patterns: list[str] | None = None,
        max_content_size_bytes: int = 500_000,
    ) -> Dict[str, Any]:
        return metadata

    fake_llm = FakeLLMClient()
    fake_image = FakeImageClient()

    monkeypatch.setattr("src.renderer.analyze_repository", fake_analyze_repository)
    monkeypatch.setattr("src.renderer.LLMClient.from_config", lambda config: fake_llm)
    monkeypatch.setattr("src.renderer.ImageClient.from_config", lambda config: fake_image)

    config = Config.from_env(output_dir=str(tmp_path), debug=False, render_mode="html-image")
    renderer = ComicRenderer(config)
    result = renderer.render(str(tmp_path))

    prompt_files = [Path(p) for p in result["prompt_files"]]
    assert len(prompt_files) == 4
    assert all(path.exists() for path in prompt_files)
    expected_prompt = (
        "Comic book panel, clean line art, tech humor style. Written text is allowed but must be "
        "English only — Latin alphabet, no foreign scripts, no gibberish, no made-up words. "
        "Keep any labels or captions short (1-4 words). English-speaking characters only: "
        "First prompt text."
    )
    assert prompt_files[0].read_text(encoding="utf-8") == expected_prompt

    image_files = [Path(p) for p in result["image_files"]]
    assert len(image_files) == 4
    assert all(path.parent.name == "images" for path in image_files)
    assert (tmp_path / "images" / "panel-1.png").exists()
    assert image_files[0].read_text(encoding="utf-8") == f"IMAGE GENERATED FROM: {expected_prompt}"

    expected_html_path = tmp_path / f"{tmp_path.name}-comic.html"
    assert result["html_file"] == str(expected_html_path)
    html_content = expected_html_path.read_text(encoding="utf-8")
    assert '<img src="images/panel-1.png"' in html_content
    assert 'class="mermaid"' not in html_content
    assert result["render_mode_used"] == "html-image"

    assert len(fake_image.generated) == 4
    assert fake_image.generated[1]["prompt"] == (
        "Comic book panel, clean line art, tech humor style. Written text is allowed but must be "
        "English only — Latin alphabet, no foreign scripts, no gibberish, no made-up words. "
        "Keep any labels or captions short (1-4 words). English-speaking characters only: "
        "Second prompt text."
    )


def test_renderer_html_mermaid_mode_produces_comic_html(tmp_path: Path, monkeypatch) -> None:
    metadata = {
        "path": str(tmp_path),
        "top_level": ["src"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "total_files": 1,
        "context_mode": "lightweight",
        "content_warnings": [],
        "files_analyzed": 0,
    }

    def fake_analyze_repository(
        repo_path: str,
        context_mode: str = "lightweight",
        custom_ignore_patterns: list[str] | None = None,
        max_content_size_bytes: int = 500_000,
    ) -> Dict[str, Any]:
        return metadata

    image_called = {"called": False}

    def fake_image_from_config(config: Any) -> FakeImageClient:
        image_called["called"] = True
        return FakeImageClient()

    monkeypatch.setattr("src.renderer.analyze_repository", fake_analyze_repository)
    monkeypatch.setattr("src.renderer.LLMClient.from_config", lambda config: FakeLLMClient())
    monkeypatch.setattr("src.renderer.ImageClient.from_config", fake_image_from_config)

    config = Config.from_env(output_dir=str(tmp_path), debug=False, render_mode="html-mermaid")
    renderer = ComicRenderer(config)
    result = renderer.render(str(tmp_path))

    assert not image_called["called"]
    expected_html_path = tmp_path / f"{tmp_path.name}-comic.html"
    assert result["html_file"] == str(expected_html_path)
    assert expected_html_path.exists()
    html_content = expected_html_path.read_text(encoding="utf-8")
    assert "comic-grid" in html_content
    assert "speech-bubble" in html_content
    assert "Hello repo!" in html_content
    assert result["render_mode_used"] == "html-mermaid"


def test_renderer_auto_fallback_on_image_failure(tmp_path: Path, monkeypatch) -> None:
    metadata = {
        "path": str(tmp_path),
        "top_level": ["src"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "total_files": 1,
        "context_mode": "lightweight",
        "content_warnings": [],
        "files_analyzed": 0,
    }

    def fake_analyze_repository(
        repo_path: str,
        context_mode: str = "lightweight",
        custom_ignore_patterns: list[str] | None = None,
        max_content_size_bytes: int = 500_000,
    ) -> Dict[str, Any]:
        return metadata

    monkeypatch.setattr("src.renderer.analyze_repository", fake_analyze_repository)
    monkeypatch.setattr("src.renderer.LLMClient.from_config", lambda config: FakeLLMClient())
    monkeypatch.setattr("src.renderer.ImageClient.from_config", lambda config: FailingImageClient())

    config = Config.from_env(output_dir=str(tmp_path), debug=False, render_mode="html-image")
    renderer = ComicRenderer(config)
    result = renderer.render(str(tmp_path))

    expected_html_path = tmp_path / f"{tmp_path.name}-comic.html"
    assert result["fallback"] == "html-mermaid"
    assert result["render_mode_used"] == "html-mermaid"
    assert result["html_file"] == str(expected_html_path)
    assert expected_html_path.exists()
    assert len(result["image_files"]) == 0
