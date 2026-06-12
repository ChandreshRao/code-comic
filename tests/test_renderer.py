from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from src.config import Config
from src.renderer import ComicRenderer


class FakeLLMClient:
    def generate_text(self, prompt: str) -> str:
        return (
            '[{"title": "Scene 1", "description": "Intro.", "panel_text": "First prompt text."}, '
            '{"title": "Scene 2", "description": "Build.", "panel_text": "Second prompt text."}, '
            '{"title": "Scene 3", "description": "Review.", "panel_text": "Third prompt text."}, '
            '{"title": "Scene 4", "description": "Ship.", "panel_text": "Fourth prompt text."}]'
        )


class FakeImageClient:
    def __init__(self) -> None:
        self.generated: list[Dict[str, Any]] = []

    def generate_image(self, prompt: str, output_path: Path) -> Path:
        output_path.write_text(f"IMAGE GENERATED FROM: {prompt}", encoding="utf-8")
        self.generated.append({"prompt": prompt, "path": output_path})
        return output_path


def test_renderer_saves_prompt_files_and_uses_them(tmp_path: Path, monkeypatch) -> None:
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

    config = Config.from_env(output_dir=str(tmp_path), debug=False)
    renderer = ComicRenderer(config)
    result = renderer.render(str(tmp_path), generate_images=True)

    prompt_files = [Path(p) for p in result["prompt_files"]]
    assert len(prompt_files) == 4
    assert all(path.exists() for path in prompt_files)
    assert prompt_files[0].read_text(encoding="utf-8") == "First prompt text."

    image_files = [Path(p) for p in result["image_files"]]
    assert len(image_files) == 4
    assert image_files[0].read_text(encoding="utf-8") == "IMAGE GENERATED FROM: First prompt text."

    assert len(fake_image.generated) == 4
    assert fake_image.generated[1]["prompt"] == "Second prompt text."


def test_renderer_writes_prompt_files_even_without_images(tmp_path: Path, monkeypatch) -> None:
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

    fake_llm = FakeLLMClient()

    monkeypatch.setattr("src.renderer.analyze_repository", fake_analyze_repository)
    monkeypatch.setattr("src.renderer.LLMClient.from_config", lambda config: fake_llm)
    monkeypatch.setattr("src.renderer.ImageClient.from_config", lambda config: FakeImageClient())

    config = Config.from_env(output_dir=str(tmp_path), debug=False)
    renderer = ComicRenderer(config)
    result = renderer.render(str(tmp_path), generate_images=False)

    prompt_files = [Path(p) for p in result["prompt_files"]]
    assert len(prompt_files) == 4
    assert all(path.exists() for path in prompt_files)
    assert (tmp_path / "panel-1.txt").exists()
    assert "IMAGE GENERATED FROM" not in (tmp_path / "panel-1.txt").read_text(encoding="utf-8")
