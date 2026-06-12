from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict

from .utils import normalize_repo_path


def analyze_repository(repo_path: str) -> Dict[str, object]:
    root = normalize_repo_path(repo_path)
    top_level = sorted([p.name for p in root.iterdir()])

    file_counts = Counter()
    all_files = []
    package_files = []
    detections = []

    for path in root.rglob("*"):
        if path.is_file():
            suffix = path.suffix.lower() or "<no-ext>"
            file_counts[suffix] += 1
            all_files.append(path.relative_to(root).as_posix())
            if path.name in {"pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "package.json"}:
                package_files.append(path.relative_to(root).as_posix())
            if path.name.lower() in {"readme.md", "readme.rst", "readme.txt"}:
                detections.append("README")

    languages = sorted({suffix.lstrip(".") for suffix in file_counts if suffix != "<no-ext>"})
    return {
        "path": str(root),
        "top_level": top_level,
        "languages": languages,
        "file_counts": dict(file_counts),
        "package_files": sorted(package_files),
        "detected_features": sorted(detections),
        "total_files": sum(file_counts.values()),
        "sample_files": all_files[:25],
    }
