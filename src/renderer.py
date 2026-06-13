from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyzer import analyze_repository
from .log_setup import get_logger
from .html_renderer import render_comic_html, render_comic_html_with_images
from .image_client import ImageClient
from .llm_client import LLMClient
from .prompt_generator import (
    build_scene_prompt,
    resolve_scenes,
)
from .utils import ensure_output_dir, save_json, save_text

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
logger = get_logger("renderer")


def _image_prompt_prefix() -> str:
    path = _PROMPTS_DIR / "image_prompt_prefix.txt"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return (
        "Comic book panel, clean line art, tech humor style, "
        "no written text or captions in the image: "
    )


def _scene_prompt_text(scene: dict, *, for_image: bool = False) -> str:
    if for_image:
        panel_text = scene.get("panel_text") or scene.get("speech_bubble", "")
        return f"{_image_prompt_prefix()} {panel_text}"
    return scene.get("speech_bubble") or scene.get("panel_text", "")


def _html_filename_from_repo(repo_path: str) -> str:
    repo_name = Path(repo_path).name
    if not repo_name:
        repo_name = "repo"
    repo_name = re.sub(r"[^A-Za-z0-9_-]+", "-", repo_name).strip("-")
    if not repo_name:
        repo_name = "repo"
    return f"{repo_name}-comic.html"


class ComicRenderer:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.llm_client = LLMClient.from_config(config)
        self._image_client: Optional[ImageClient] = None

    @property
    def image_client(self) -> ImageClient:
        if self._image_client is None:
            self._image_client = ImageClient.from_config(self.config)
        return self._image_client

    def render(self, repo_path: str) -> Dict[str, Any]:
        render_mode = getattr(self.config, "render_mode", "html-mermaid")
        metadata = analyze_repository(
            repo_path,
            context_mode=self.config.context_mode,
            custom_ignore_patterns=self.config.ignore_patterns,
            max_content_size_bytes=self.config.max_content_size_bytes,
        )

        if metadata.get("content_warnings") and self.config.debug:
            for warning in metadata["content_warnings"]:
                logger.warning("Content warning: %s", warning)

        prompt = build_scene_prompt(metadata, render_mode=render_mode)
        try:
            raw_output = self.llm_client.generate_text(prompt)
        except RuntimeError as exc:
            logger.warning("LLM generation failed (%s). Using template-based scenes.", exc)
            raw_output = "[Fallback LLM]"
        scenes = resolve_scenes(raw_output, metadata, render_mode=render_mode)

        output_dir = ensure_output_dir(self.config.output_dir)
        save_json(output_dir / "repo_metadata.json", metadata)
        save_json(output_dir / "comic_scenes.json", scenes)

        prompt_files: List[Path] = []
        image_files: List[Path] = []
        html_file: Optional[Path] = None
        render_mode_used = render_mode
        fallback: Optional[str] = None
        html_path = output_dir / _html_filename_from_repo(repo_path)

        for idx, scene in enumerate(scenes, start=1):
            prompt_text = _scene_prompt_text(scene, for_image=render_mode == "html-image")
            prompt_path = output_dir / f"prompt-{idx}.txt"
            save_text(prompt_path, prompt_text)
            prompt_files.append(prompt_path)

        if render_mode == "html-mermaid":
            html_file = render_comic_html(scenes, metadata, html_path)

        elif render_mode == "html-image":
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            image_rel_paths: List[str] = []
            image_failed = False

            for idx in range(1, len(scenes) + 1):
                output_path = images_dir / f"panel-{idx}.png"
                try:
                    prompt_text = prompt_files[idx - 1].read_text(encoding="utf-8")
                    image_path = self.image_client.generate_image(prompt_text, output_path)
                    image_files.append(image_path)
                    image_rel_paths.append(f"images/panel-{idx}.png")
                except RuntimeError as exc:
                    if not image_failed:
                        logger.warning(
                            "Image generation failed (%s). Falling back to HTML/Mermaid comic.",
                            exc,
                        )
                        image_failed = True
                    break

            if image_failed:
                scenes = resolve_scenes(raw_output, metadata, render_mode="html-mermaid")
                save_json(output_dir / "comic_scenes.json", scenes)
                for idx, scene in enumerate(scenes, start=1):
                    prompt_text = scene.get("speech_bubble") or scene.get("panel_text", "")
                    save_text(output_dir / f"prompt-{idx}.txt", prompt_text)
                html_file = render_comic_html(scenes, metadata, html_path)
                render_mode_used = "html-mermaid"
                fallback = "html-mermaid"
                image_files = []
            else:
                html_file = render_comic_html_with_images(
                    scenes, metadata, html_path, image_rel_paths
                )

        return {
            "output_dir": str(output_dir),
            "metadata": metadata,
            "scenes": scenes,
            "prompt_files": [str(path) for path in prompt_files],
            "image_files": [str(path) for path in image_files],
            "html_file": str(html_file) if html_file else None,
            "render_mode_used": render_mode_used,
            "fallback": fallback,
        }
