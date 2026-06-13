from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .content_reader import ContentReader
from .ignore_handler import IgnorePatternHandler
from .utils import normalize_repo_path


def analyze_repository(
    repo_path: str,
    context_mode: str = "lightweight",
    custom_ignore_patterns: list[str] | None = None,
    max_content_size_bytes: int = 500_000,
) -> dict[str, Any]:
    """
    Analyze repository structure and optionally gather file contents.

    Args:
        repo_path: Path to repository root
        context_mode: "lightweight" (README + docs) or "comprehensive" (full repo)
        custom_ignore_patterns: Additional patterns to ignore (merged with .gitignore)
        max_content_size_bytes: Threshold for content size warnings

    Returns:
        Dict with repo metadata and optionally file contents
    """
    root = normalize_repo_path(repo_path)

    # Initialize ignore handler
    ignore_handler = IgnorePatternHandler(
        root, custom_patterns=custom_ignore_patterns
    )

    # Analyze file structure
    top_level = sorted(
        [p.name for p in root.iterdir() if not ignore_handler.should_ignore(p)]
    )

    file_counts = Counter()
    all_files = []
    package_files = []
    detections = []

    for path in root.rglob("*"):
        if path.is_file() and not ignore_handler.should_ignore(path):
            suffix = path.suffix.lower() or "<no-ext>"
            file_counts[suffix] += 1
            all_files.append(path.relative_to(root).as_posix())
            if path.name in {
                "pyproject.toml",
                "setup.py",
                "requirements.txt",
                "Pipfile",
                "package.json",
            }:
                package_files.append(path.relative_to(root).as_posix())
            if path.name.lower() in {"readme.md", "readme.rst", "readme.txt"}:
                detections.append("README")

    languages = sorted(
        {suffix.lstrip(".") for suffix in file_counts if suffix != "<no-ext>"}
    )

    result: dict[str, Any] = {
        "path": str(root),
        "top_level": top_level,
        "languages": languages,
        "file_counts": dict(file_counts),
        "package_files": sorted(package_files),
        "detected_features": sorted(detections),
        "total_files": sum(file_counts.values()),
        "sample_files": all_files[:25],
        "context_mode": context_mode,
        "content_warnings": [],
        "files_analyzed": 0,
    }

    # Gather file contents based on context mode
    if context_mode in ("lightweight", "comprehensive"):
        content_reader = ContentReader(
            ignore_handler,
            max_file_size=1024 * 1024,  # 1MB per file
            max_total_size=max_content_size_bytes,
        )

        # Read content based on mode
        if context_mode == "lightweight":
            content = content_reader.read_profile_lightweight(root)
        else:  # comprehensive
            content = content_reader.read_profile_comprehensive(root)

        # Filter out None values (unreadable files)
        content = {k: v for k, v in content.items() if v is not None}

        # Calculate content size and warn if necessary
        total_size = content_reader.estimate_content_size(content)
        result["content"] = content
        result["files_analyzed"] = len(content)

        if total_size > max_content_size_bytes:
            size_mb = total_size / (1024 * 1024)
            threshold_mb = max_content_size_bytes / (1024 * 1024)
            result["content_warnings"].append(
                f"Comprehensive context size ({size_mb:.1f}MB) exceeds recommended threshold "
                f"({threshold_mb:.1f}MB). Consider using lightweight mode or adjusting ignore patterns."
            )

    return result
