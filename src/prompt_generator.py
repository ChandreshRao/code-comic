from __future__ import annotations

import json
from typing import Any, Dict, List


def build_scene_prompt(repo_metadata: Dict[str, Any]) -> str:
    bullets = []
    bullets.append(f"Repository path: {repo_metadata.get('path')}")
    bullets.append(f"Top-level entries: {', '.join(repo_metadata.get('top_level', [])) or 'none'}")
    bullets.append(f"Detected languages: {', '.join(repo_metadata.get('languages', [])) or 'unknown'}")
    bullets.append(f"Package files: {', '.join(repo_metadata.get('package_files', [])) or 'none'}")
    bullets.append(f"Total files: {repo_metadata.get('total_files', 0)}")
    if repo_metadata.get("detected_features"):
        bullets.append(f"Special markers: {', '.join(repo_metadata['detected_features'])}")

    return (
        "You are a developer storyteller. "
        "Create a 4-scene comic strip that explains the codebase architecture and developer workflow for the repository described below. "
        "For each scene, provide a title, a short description, and a recommended visual panel prompt. "
        "Return the result as JSON with exactly four objects, each containing the keys: title, description, panel_text. "
        "If you cannot return JSON, use clearly numbered scenes and include all required fields. "
        "Repository details:\n"
        + "\n".join(bullets)
    )


def parse_scene_output(raw_text: str) -> List[Dict[str, str]]:
    try:
        scenes = json.loads(raw_text)
        if isinstance(scenes, list) and len(scenes) == 4:
            return [
                {
                    "title": str(scene.get("title", f"Scene {idx + 1}")),
                    "description": str(scene.get("description", "")),
                    "panel_text": str(scene.get("panel_text", "")),
                }
                for idx, scene in enumerate(scenes)
            ]
    except Exception:
        pass

    sections = [part.strip() for part in raw_text.split("Scene") if part.strip()][:4]
    scenes = []
    for index, section in enumerate(sections, start=1):
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        title = lines[0] if lines else f"Scene {index}"
        description = " ".join(lines[1:3]) if len(lines) > 1 else ""
        panel_text = " ".join(lines[3:5]) if len(lines) > 3 else description
        scenes.append({"title": title, "description": description, "panel_text": panel_text})

    while len(scenes) < 4:
        scenes.append({"title": f"Scene {len(scenes) + 1}", "description": "Explain a repository concept.", "panel_text": "Show the repo architecture as a friendly illustration."})

    return scenes


def render_fallback_scenes(repo_metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    languages = ", ".join(repo_metadata.get("languages", ["unknown"]))
    package_files = ", ".join(repo_metadata.get("package_files", ["none"]))
    return [
        {
            "title": "Meet the Repository",
            "description": "Introduce the project structure, languages, and key files.",
            "panel_text": (
                f"A cheerful developer looks at a folder tree labeled with languages {languages} "
                f"and package files {package_files}."
            ),
        },
        {
            "title": "How Code Organizes",
            "description": "Show top-level modules, directories, and main application flow.",
            "panel_text": (
                f"A diagram of top-level repo entries {repo_metadata.get('top_level', [])} "
                "with arrows showing how code components connect."
            ),
        },
        {
            "title": "Dependencies and Tools",
            "description": "Explain dependency files and the environment used to run the code.",
            "panel_text": (
                "A toolbox labeled with requirements, pyproject, and package manager icons "
                "next to a terminal running install commands."
            ),
        },
        {
            "title": "Developer Journey",
            "description": "Wrap up with how contributors should read and extend the repo.",
            "panel_text": (
                "A developer on a ladder climbing into a repo tree, holding a guidebook titled 'Architectural overview'."
            ),
        },
    ]
