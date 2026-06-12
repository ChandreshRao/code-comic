from src.prompt_generator import build_scene_prompt, parse_scene_output, render_fallback_scenes


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
    assert "exactly four objects" in prompt


def test_parse_scene_output_falls_back_on_non_json() -> None:
    raw_text = "Scene 1: Intro\nA short description.\nScene 2: Overview\nA short description."
    scenes = parse_scene_output(raw_text)

    assert len(scenes) == 4
    assert scenes[0]["title"].startswith("1") or scenes[0]["title"]
    assert scenes[1]["description"] != ""


def test_render_fallback_scenes_produces_four_scenes() -> None:
    metadata = {"languages": ["py"], "package_files": ["pyproject.toml"], "top_level": ["src"]}
    scenes = render_fallback_scenes(metadata)

    assert len(scenes) == 4
    assert scenes[0]["title"] == "Meet the Repository"
