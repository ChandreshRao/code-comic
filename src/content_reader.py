"""Read and manage file contents for repo context gathering."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ignore_handler import IgnorePatternHandler

import fnmatch


class ContentReader:
    """Read file contents while respecting ignore patterns and file size limits."""

    # Text file extensions to consider
    TEXT_EXTENSIONS = {
        ".md",
        ".txt",
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kotlin",
        ".sh",
        ".bash",
        ".Dockerfile",
        ".makefile",
        ".Makefile",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".sql",
        ".r",
        ".R",
    }

    # Binary file extensions to skip
    BINARY_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".svg",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".pyc",
        ".o",
        ".a",
    }

    def __init__(
        self,
        ignore_handler: IgnorePatternHandler,
        max_file_size: int = 1024 * 1024,  # 1MB per file
        max_total_size: int = 10 * 1024 * 1024,  # 10MB total
    ):
        """
        Initialize content reader.

        Args:
            ignore_handler: IgnorePatternHandler instance
            max_file_size: Max size per file in bytes (files exceeding this are truncated with warning)
            max_total_size: Max total content size in bytes (warning issued if exceeded)
        """
        self.ignore_handler = ignore_handler
        self.max_file_size = max_file_size
        self.max_total_size = max_total_size

    def _is_text_file(self, path: Path) -> bool:
        """Check if file is likely a text file."""
        suffix = path.suffix.lower()

        # Check binary extensions first
        if suffix in self.BINARY_EXTENSIONS:
            return False

        # Check text extensions
        if suffix in self.TEXT_EXTENSIONS:
            return True

        # Check filename for common patterns
        name = path.name.lower()
        if name in {
            "makefile",
            "dockerfile",
            "gemfile",
            "rakefile",
            ".gitignore",
            ".gitattributes",
            ".editorconfig",
            "license",
            "readme",
            "changelog",
            "contributing",
        }:
            return True

        # If no extension and looks like config file
        if not suffix and (name.startswith(".") or name.isupper()):
            return True

        return False

    def read_file_content(
        self,
        path: Path,
        encoding: str = "utf-8",
        fallback_encoding: str = "latin-1",
    ) -> str | None:
        """
        Read file content with encoding fallback.

        Args:
            path: Path to file
            encoding: Primary encoding to try
            fallback_encoding: Fallback encoding if primary fails

        Returns:
            File content as string, or None if file can't be read
        """
        if not path.is_file() or self.ignore_handler.should_ignore(path):
            return None

        # Check file size
        try:
            size = path.stat().st_size
            if size > self.max_file_size:
                return None  # Skip large files
        except (OSError, PermissionError):
            return None

        # Try reading with primary encoding, then fallback
        for enc in [encoding, fallback_encoding]:
            try:
                with open(path, encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, OSError, PermissionError):
                continue

        return None  # File is binary or unreadable

    def read_files_matching(
        self,
        patterns: list[str] | str,
        root: Path | None = None,
        max_files: int | None = None,
    ) -> dict[str, str | None]:
        """
        Find and read files matching glob patterns.

        Args:
            patterns: Glob pattern(s) (e.g., "*.md" or ["*.md", "docs/*.md"])
            root: Starting directory (default: repo_root)
            max_files: Maximum number of files to read

        Returns:
            Dict mapping relative file paths to contents (None if unreadable)
        """
        if isinstance(patterns, str):
            patterns = [patterns]

        root = Path(root or self.ignore_handler.repo_root)
        result = {}
        count = 0

        # Find all matching files
        for pattern in patterns:
            for match in sorted(root.glob(pattern)):
                if match.is_file() and not self.ignore_handler.should_ignore(match):
                    if max_files and count >= max_files:
                        break

                    rel_path = match.relative_to(root)
                    content = self.read_file_content(match)
                    result[str(rel_path).replace("\\", "/")] = content
                    count += 1

            if max_files and count >= max_files:
                break

        return result

    def read_profile_lightweight(self, repo_root: Path) -> dict[str, str | None]:
        """
        Read files for lightweight context mode.

        Returns README + CONTRIBUTING.md + docs/*.md files.
        """
        content = {}

        # README patterns
        for readme_pattern in ["README*", "readme*"]:
            matches = self.read_files_matching(readme_pattern, repo_root, max_files=1)
            content.update(matches)
            if matches:
                break

        # CONTRIBUTING.md
        contributing = self.read_files_matching(
            "*CONTRIBUTING*", repo_root, max_files=1
        )
        content.update(contributing)

        # docs/*.md and docs/**/*.md
        docs_content = self.read_files_matching(
            ["docs/**/*.md", "docs/*.md"], repo_root, max_files=20
        )
        content.update(docs_content)

        return content

    def read_profile_comprehensive(
        self, repo_root: Path
    ) -> dict[str, str | None]:
        """
        Read files for comprehensive context mode.

        Returns lightweight profile + all source code + all .md files + config files.
        """
        content = self.read_profile_lightweight(repo_root)

        # All markdown files
        markdown_files = self.read_files_matching("**/*.md", repo_root)
        content.update(markdown_files)

        # All source code files (by extension)
        source_extensions = [
            "*.py",
            "*.js",
            "*.ts",
            "*.tsx",
            "*.jsx",
            "*.java",
            "*.go",
            "*.rs",
            "*.c",
            "*.cpp",
            "*.cs",
            "*.rb",
            "*.php",
            "*.swift",
        ]
        for ext in source_extensions:
            source_files = self.read_files_matching(f"**/{ext}", repo_root)
            content.update(source_files)

        # Common config files
        config_patterns = [
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "package.json",
            "tsconfig.json",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Makefile",
            ".dockerignore",
            "*.env.example",
            ".env.example",
        ]
        for pattern in config_patterns:
            config_files = self.read_files_matching(pattern, repo_root)
            content.update(config_files)

        return content

    def estimate_content_size(self, content: dict[str, str | None]) -> int:
        """
        Estimate total size of content in bytes.

        Args:
            content: Dict of filepath -> content

        Returns:
            Total size estimate in bytes
        """
        total = 0
        for filepath, file_content in content.items():
            total += len(filepath.encode("utf-8"))
            if file_content:
                total += len(file_content.encode("utf-8"))
        return total
