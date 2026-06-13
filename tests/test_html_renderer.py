from __future__ import annotations

from pathlib import Path

from src.html_renderer import _templates_dir, render_comic_html, render_comic_html_with_images
from src.prompt_generator import _build_fallback_mermaid, build_scene_prompt


def test_html_templates_exist_in_repo() -> None:
    templates_dir = _templates_dir()
    assert (templates_dir / "comic-mermaid.html").exists()
    assert (templates_dir / "comic-image.html").exists()
    assert (templates_dir / "panel-mermaid.html").exists()
    assert (templates_dir / "panel-image.html").exists()


def test_build_scene_prompt_html_mode_asks_for_mermaid() -> None:
    metadata = {
        "path": "/tmp/repo",
        "top_level": ["src"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "total_files": 10,
    }

    prompt = build_scene_prompt(metadata, render_mode="html-mermaid")

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


def test_render_comic_html_with_images_creates_img_tags(tmp_path: Path) -> None:
    scenes = [
        {
            "title": "Panel 1",
            "description": "Intro scene.",
            "speech_bubble": "Hello world!",
            "panel_text": "Hello world!",
        },
        {
            "title": "Panel 2",
            "description": "Build scene.",
            "speech_bubble": "Building features.",
            "panel_text": "Building features.",
        },
        {
            "title": "Panel 3",
            "description": "Review scene.",
            "speech_bubble": "Code review time.",
            "panel_text": "Code review time.",
        },
        {
            "title": "Panel 4",
            "description": "Ship scene.",
            "speech_bubble": "Ship it!",
            "panel_text": "Ship it!",
        },
    ]
    metadata = {"path": "/tmp/repo", "languages": ["py"], "total_files": 42}
    image_rel_paths = [f"images/panel-{i}.png" for i in range(1, 5)]

    output_path = tmp_path / "sample-repo-comic.html"
    result = render_comic_html_with_images(scenes, metadata, output_path, image_rel_paths)

    assert result == output_path
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "comic-grid" in content
    assert '<img src="images/panel-1.png"' in content
    assert 'class="mermaid"' not in content
    assert "speech-bubble" in content
    assert "mermaid.esm.min.mjs" not in content
