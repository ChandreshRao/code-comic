"""Handle .gitignore patterns and custom ignore patterns for repo analysis."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

import fnmatch


class IgnorePatternHandler:
    """Manage .gitignore and custom ignore patterns for repo context gathering."""

    # Default patterns to always ignore (built-in)
    DEFAULT_IGNORE_PATTERNS = {
        # Version control
        ".git",
        ".gitignore",
        # Python environments
        ".venv",
        "venv",
        "env",
        ".env",
        ".env.local",
        ".env.*.local",
        "__pycache__",
        "*.py[cod]",
        "*$py.class",
        "*.egg-info",
        ".eggs",
        "eggs",
        "build",
        "dist",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        # Node environments
        "node_modules",
        "npm-debug.log",
        "yarn-error.log",
        # IDE
        ".vscode",
        ".idea",
        "*.swp",
        "*.swo",
        "*~",
        ".DS_Store",
        # Build outputs
        "*.o",
        "*.a",
        "*.so",
        "*.dylib",
        "*.dll",
        "*.exe",
        # Temporary/cache
        ".cache",
        ".tmp*",
        "tmp",
        "temp",
        "*.tmp",
        "*.temp",
        # Package extraction directories
        ".whl*",
        ".egg*",
        ".extracted*",
        # Other common ignores
        "*.log",
        ".coverage",
        "htmlcov",
        ".hypothesis",
        ".pytest",
        "site-packages",
    }

    def __init__(self, repo_root: Path, custom_patterns: list[str] | None = None):
        """
        Initialize ignore pattern handler.

        Args:
            repo_root: Root path of the repository
            custom_patterns: Additional patterns to ignore (in gitignore format)
        """
        self.repo_root = Path(repo_root).resolve()
        self.patterns = set(self.DEFAULT_IGNORE_PATTERNS)

        # Load .gitignore if it exists
        gitignore_path = self.repo_root / ".gitignore"
        if gitignore_path.exists():
            self._load_gitignore(gitignore_path)

        # Add custom patterns
        if custom_patterns:
            self.patterns.update(custom_patterns)

    def _load_gitignore(self, gitignore_path: Path) -> None:
        """Parse .gitignore file and add patterns."""
        try:
            with open(gitignore_path) as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        self.patterns.add(line)
        except OSError:
            pass  # Silently ignore if .gitignore can't be read

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored.

        Args:
            path: Path to check (can be relative or absolute)

        Returns:
            True if path matches any ignore pattern, False otherwise
        """
        # Resolve to absolute for consistent comparison
        try:
            path = path.resolve()
        except (OSError, ValueError):
            return True  # Ignore paths that can't be resolved (e.g., broken symlinks)

        # Get relative path from repo root
        try:
            rel_path = path.relative_to(self.repo_root)
        except ValueError:
            # Path is outside repo, check against filename only
            rel_path = path

        path_str = str(rel_path).replace("\\", "/")  # Normalize to forward slashes
        path_parts = path_str.split("/")
        name = path.name

        # Check against all patterns
        for pattern in self.patterns:
            # Normalize pattern (remove trailing slash for directory matching)
            pattern_normalized = pattern.rstrip("/")

            # Check full path
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(path_str, f"**/{pattern}"):
                return True
            # Check full path against normalized pattern (for dirs)
            if fnmatch.fnmatch(path_str, pattern_normalized):
                return True
            if fnmatch.fnmatch(path_str, f"**/{pattern_normalized}"):
                return True
            # Check each path component
            if fnmatch.fnmatch(name, pattern_normalized):
                return True
            # Check for directory matches
            for part in path_parts:
                if fnmatch.fnmatch(part, pattern_normalized):
                    return True

        return False

    def walk_files(
        self,
        root: Path | None = None,
        file_filter: Callable[[Path], bool] | None = None,
    ) -> list[Path]:
        """
        Walk repo and yield non-ignored files.

        Args:
            root: Starting directory (default: repo_root)
            file_filter: Optional function to further filter files

        Yields:
            Path objects for non-ignored files
        """
        root = Path(root or self.repo_root)
        files = []

        try:
            for path in root.rglob("*"):
                if path.is_file() and not self.should_ignore(path):
                    if file_filter is None or file_filter(path):
                        files.append(path)
        except (OSError, PermissionError):
            pass  # Silently skip inaccessible directories

        return sorted(files)
