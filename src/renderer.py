from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .analyzer import analyze_repository
from .image_client import ImageClient
from .llm_client import LLMClient
from .prompt_generator import (
    build_scene_prompt,
    parse_scene_output,
    render_fallback_scenes,
)
from .utils import ensure_output_dir, save_json, save_text


class ComicRenderer:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.llm_client = LLMClient.from_config(config)
        self.image_client = ImageClient.from_config(config)

    def render(self, repo_path: str, generate_images: bool = True) -> Dict[str, Any]:
        metadata = analyze_repository(repo_path)
        prompt = build_scene_prompt(metadata)
        raw_output = self.llm_client.generate_text(prompt)
        scenes = parse_scene_output(raw_output)

        if not scenes or raw_output.startswith("[Fallback LLM]"):
            scenes = render_fallback_scenes(metadata)

        output_dir = ensure_output_dir(self.config.output_dir)
        save_json(output_dir / "repo_metadata.json", metadata)
        save_json(output_dir / "comic_scenes.json", scenes)

        prompt_files: List[Path] = []
        image_files: List[Path] = []
        for idx, scene in enumerate(scenes, start=1):
            prompt_path = output_dir / f"prompt-{idx}.txt"
            save_text(prompt_path, scene["panel_text"])
            prompt_files.append(prompt_path)

            output_path = output_dir / f"panel-{idx}.png"
            if generate_images:
                prompt_text = prompt_path.read_text(encoding="utf-8")
                image_path = self.image_client.generate_image(prompt_text, output_path)
            else:
                image_path = output_path.with_suffix(".txt")
                save_text(image_path, scene["panel_text"])
            image_files.append(image_path)

        return {
            "output_dir": str(output_dir),
            "metadata": metadata,
            "scenes": scenes,
            "prompt_files": [str(path) for path in prompt_files],
            "image_files": [str(path) for path in image_files],
        }
