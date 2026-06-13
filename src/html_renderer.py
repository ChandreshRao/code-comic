from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List

from .utils import save_text

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_DEFAULT_MERMAID = 'flowchart TD\n    A["Architecture"] --> B["Details"]'


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _repo_display_name(metadata: Dict[str, Any]) -> str:
    repo_path = metadata.get("path", "Repository")
    if not repo_path or repo_path == "Repository":
        return "Repository"
    return Path(str(repo_path)).name or str(repo_path)


def _templates_dir() -> Path:
    return _TEMPLATES_DIR


def _load_template(name: str) -> str:
    path = _templates_dir() / name
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _render_template(template: str, mapping: Dict[str, str]) -> str:
    try:
        return template.format(**mapping)
    except Exception:
        return template


def _panel_html(scene: Dict[str, str], index: int) -> str:
    template = _load_template("panel-mermaid.html")
    if not template:
        raise FileNotFoundError(
            f"Missing panel template: {_templates_dir() / 'panel-mermaid.html'}"
        )

    title = _escape(scene.get("title", f"Panel {index}"))
    description = _escape(scene.get("description", ""))
    speech = _escape(scene.get("speech_bubble") or scene.get("panel_text", ""))
    mermaid = scene.get("mermaid", "").strip() or _DEFAULT_MERMAID

    return _render_template(
        template,
        {
            "index": str(index),
            "title": title,
            "description": description,
            "speech": speech,
            "mermaid": mermaid,
        },
    )


def render_comic_html(
    scenes: List[Dict[str, str]],
    metadata: Dict[str, Any],
    output_path: Path,
) -> Path:
    template = _load_template("comic-mermaid.html")
    if not template:
        raise FileNotFoundError(
            f"Missing comic template: {_templates_dir() / 'comic-mermaid.html'}"
        )

    page_title = _escape(f"Code Comic: {_repo_display_name(metadata)}")
    languages = _escape(", ".join(metadata.get("languages", [])) or "unknown")
    total_files = str(metadata.get("total_files", 0))

    panels = "\n".join(_panel_html(scene, idx) for idx, scene in enumerate(scenes[:4], start=1))

    document = _render_template(
        template,
        {
            "page_title": page_title,
            "languages": languages,
            "total_files": total_files,
            "panels": panels,
        },
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")

    for idx, scene in enumerate(scenes[:4], start=1):
        mermaid = scene.get("mermaid", "").strip()
        if mermaid:
            save_text(output_path.parent / f"panel-{idx}.mmd", mermaid)

    return output_path


def _panel_html_image(scene: Dict[str, str], index: int, image_rel_path: str) -> str:
    template = _load_template("panel-image.html")
    if not template:
        raise FileNotFoundError(
            f"Missing panel template: {_templates_dir() / 'panel-image.html'}"
        )

    title = _escape(scene.get("title", f"Panel {index}"))
    description = _escape(scene.get("description", ""))
    speech = _escape(scene.get("speech_bubble") or scene.get("panel_text", ""))
    image_src = _escape(image_rel_path)

    return _render_template(
        template,
        {
            "index": str(index),
            "title": title,
            "description": description,
            "speech": speech,
            "image_src": image_src,
        },
    )


def render_comic_html_with_images(
    scenes: List[Dict[str, str]],
    metadata: Dict[str, Any],
    output_path: Path,
    image_rel_paths: List[str],
) -> Path:
    template = _load_template("comic-image.html")
    if not template:
        raise FileNotFoundError(
            f"Missing comic template: {_templates_dir() / 'comic-image.html'}"
        )

    page_title = _escape(f"Code Comic: {_repo_display_name(metadata)}")
    languages = _escape(", ".join(metadata.get("languages", [])) or "unknown")
    total_files = str(metadata.get("total_files", 0))

    panels = "\n".join(
        _panel_html_image(scene, idx, image_rel_paths[idx - 1])
        for idx, scene in enumerate(scenes[:4], start=1)
    )

    document = _render_template(
        template,
        {
            "page_title": page_title,
            "languages": languages,
            "total_files": total_files,
            "panels": panels,
        },
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
