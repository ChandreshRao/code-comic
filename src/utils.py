from __future__ import annotations

import json
from pathlib import Path


def normalize_repo_path(repo_path: str) -> Path:
    path = Path(repo_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Repository path not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path}")
    return path


def ensure_output_dir(output_dir: str) -> Path:
    path = Path(output_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def save_text(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)
