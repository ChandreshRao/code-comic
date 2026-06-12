from src.prompt_generator import (
    build_scene_prompt,
    enrich_scenes,
    parse_scene_output,
    render_fallback_scenes,
    resolve_scenes,
    scenes_are_valid,
)


def test_build_scene_prompt_contains_repo_details() -> None:
    metadata = {
        "path": "/tmp/repo",
        "top_level": ["src", "README.md"],
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "total_files": 10,
        "detected_features": ["README"],
    }

    prompt = build_scene_prompt(metadata)

    assert "Repository path: /tmp/repo" in prompt
    assert "Detected languages: py" in prompt
    assert "raw JSON array" in prompt


def test_parse_scene_output_falls_back_on_non_json() -> None:
    raw_text = "Scene 1: Intro\nA short description.\nScene 2: Overview\nA short description."
    scenes = parse_scene_output(raw_text)

    assert len(scenes) == 4
    assert scenes[0]["title"].startswith("1") or scenes[0]["title"]
    assert scenes[1]["description"] != ""


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
    assert "witty tech comic" in prompt


def test_render_fallback_scenes_includes_mermaid() -> None:
    metadata = {
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "top_level": ["src"],
        "content": {"README.md": "# TinyCalc\n\nA calculator."},
        "sample_files": ["src/main.py", "src/calculator.py"],
    }
    scenes = render_fallback_scenes(metadata)

    assert len(scenes) == 4
    assert "TinyCalc" in scenes[0]["title"]
    assert scenes[0]["mermaid"]
    assert len(scenes[0]["speech_bubble"]) < 100


def test_parse_scene_output_handles_markdown_fenced_json() -> None:
    raw_text = """```json
[
  {
    "title": "Meet TinyCalc",
    "description": "Introduce the calculator project.",
    "speech_bubble": "Welcome to TinyCalc!",
    "mermaid": "flowchart TD\\n    A --> B"
  },
  {
    "title": "Code Flow",
    "description": "How modules connect.",
    "speech_bubble": "main.py calls calculator.py.",
    "mermaid": "flowchart LR\\n    main --> calculator"
  },
  {
    "title": "Dependencies",
    "description": "Project tooling.",
    "speech_bubble": "Check pyproject.toml first.",
    "mermaid": "flowchart TD\\n    Tools --> pyproject"
  },
  {
    "title": "Developer Journey",
    "description": "How to contribute.",
    "speech_bubble": "Read the README and run the CLI.",
    "mermaid": "flowchart TD\\n    Dev --> Ship"
  }
]
```"""
    scenes = parse_scene_output(raw_text)

    assert len(scenes) == 4
    assert scenes[0]["title"] == "Meet TinyCalc"
    assert scenes[0]["speech_bubble"] == "Welcome to TinyCalc!"
    assert scenes_are_valid(scenes)


def test_resolve_scenes_rejects_garbage_and_uses_metadata_fallback() -> None:
    metadata = {
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "top_level": ["README.md", "src"],
        "sample_files": ["src/main.py", "src/calculator.py"],
        "content": {"README.md": "# TinyCalc\n\nA calculator."},
    }
    garbage = "```json\n[ { \"title\": \"Meet TinyCalc!\""
    scenes = resolve_scenes(garbage, metadata, render_mode="html")

    assert "TinyCalc" in scenes[0]["title"]
    assert "main.py" in scenes[1]["mermaid"] or "calculator" in scenes[1]["mermaid"]


def test_enrich_scenes_fills_missing_mermaid_from_repo_files() -> None:
    metadata = {
        "languages": ["py"],
        "package_files": ["pyproject.toml"],
        "top_level": ["README.md", "src"],
        "sample_files": ["src/main.py", "src/calculator.py"],
    }
    partial = [
        {
            "title": "Custom Title",
            "description": "Custom description.",
            "speech_bubble": "Custom bubble.",
            "panel_text": "Custom bubble.",
            "mermaid": "",
        }
    ] + render_fallback_scenes(metadata)[1:]

    enriched = enrich_scenes(partial, metadata)

    assert enriched[0]["title"] == "Custom Title"
    assert enriched[0]["mermaid"]
    assert "main.py" in enriched[1]["mermaid"] or "calculator" in enriched[1]["mermaid"]
