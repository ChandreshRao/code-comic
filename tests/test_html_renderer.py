from __future__ import annotations

from pathlib import Path

from src.html_renderer import render_comic_html
from src.prompt_generator import _build_fallback_mermaid, build_scene_prompt


def test_build_scene_prompt_html_mode_asks_for_mermaid() -> None:
    metadata = {
        "path": "/tmp/repo",
        "top_level": ["src"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "total_files": 10,
    }

    prompt = build_scene_prompt(metadata, render_mode="html")

    assert "speech_bubble" in prompt
    assert "mermaid" in prompt
    assert "panel_text" not in prompt


def test_render_comic_html_creates_file_with_mermaid_and_bubbles(tmp_path: Path) -> None:
    scenes = [
        {
            "title": "Panel 1",
            "description": "Intro scene.",
            "speech_bubble": 'Hello <script>alert("x")</script> world!',
            "mermaid": "flowchart TD\n    A --> B",
        },
        {
            "title": "Panel 2",
            "description": "Build scene.",
            "speech_bubble": "Building features.",
            "mermaid": "flowchart TD\n    B --> C",
        },
        {
            "title": "Panel 3",
            "description": "Review scene.",
            "speech_bubble": "Code review time.",
            "mermaid": "flowchart TD\n    C --> D",
        },
        {
            "title": "Panel 4",
            "description": "Ship scene.",
            "speech_bubble": "Ship it!",
            "mermaid": "flowchart TD\n    D --> E",
        },
    ]
    metadata = {"path": "/tmp/repo", "languages": ["py"], "total_files": 42}

    output_path = tmp_path / "comic.html"
    result = render_comic_html(scenes, metadata, output_path)

    assert result == output_path
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "comic-grid" in content
    assert 'class="mermaid"' in content
    assert "speech-bubble" in content
    assert "Hello &lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; world!" in content
    assert "<script>alert" not in content
    assert (tmp_path / "panel-1.mmd").exists()


def test_build_fallback_mermaid_produces_valid_syntax() -> None:
    metadata = {
        "top_level": ["src", "README.md", "tests"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
    }

    for idx in range(4):
        diagram = _build_fallback_mermaid(metadata, idx)
        assert "flowchart" in diagram
        assert "-->" in diagram
