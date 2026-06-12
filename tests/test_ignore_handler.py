"""Tests for ignore_handler module."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.ignore_handler import IgnorePatternHandler


class TestIgnorePatternHandler:
    """Test suite for IgnorePatternHandler."""

    def test_default_patterns_are_applied(self):
        """Test that default patterns are always applied."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            handler = IgnorePatternHandler(repo_root)

            # Create test files
            (repo_root / "node_modules").mkdir()
            (repo_root / "node_modules" / "package.json").touch()
            (repo_root / ".venv").mkdir()
            (repo_root / ".venv" / "pyvenv.cfg").touch()
            (repo_root / "src").mkdir()
            (repo_root / "src" / "main.py").touch()

            # Test that default patterns are ignored
            assert handler.should_ignore(repo_root / "node_modules")
            assert handler.should_ignore(repo_root / "node_modules" / "package.json")
            assert handler.should_ignore(repo_root / ".venv")
            assert handler.should_ignore(repo_root / ".venv" / "pyvenv.cfg")

            # Test that normal files are not ignored
            assert not handler.should_ignore(repo_root / "src")
            assert not handler.should_ignore(repo_root / "src" / "main.py")

    def test_custom_patterns_are_merged(self):
        """Test that custom patterns are merged with defaults."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            handler = IgnorePatternHandler(
                repo_root, custom_patterns=["*.tmp", "custom_dir/"]
            )

            (repo_root / "test.tmp").touch()
            (repo_root / "custom_dir").mkdir()
            (repo_root / "custom_dir" / "file.txt").touch()
            (repo_root / "normal.py").touch()

            assert handler.should_ignore(repo_root / "test.tmp")
            assert handler.should_ignore(repo_root / "custom_dir")
            assert handler.should_ignore(repo_root / "custom_dir" / "file.txt")
            assert not handler.should_ignore(repo_root / "normal.py")

    def test_gitignore_patterns_are_loaded(self):
        """Test that .gitignore patterns are loaded and respected."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create .gitignore file
            gitignore = repo_root / ".gitignore"
            gitignore.write_text("*.log\nbuild/\ndist/\n")

            handler = IgnorePatternHandler(repo_root)

            (repo_root / "app.log").touch()
            (repo_root / "build").mkdir()
            (repo_root / "build" / "output.bin").touch()
            (repo_root / "dist").mkdir()
            (repo_root / "main.py").touch()

            assert handler.should_ignore(repo_root / "app.log")
            assert handler.should_ignore(repo_root / "build")
            assert handler.should_ignore(repo_root / "dist")
            assert not handler.should_ignore(repo_root / "main.py")

    def test_walk_files_respects_ignore_patterns(self):
        """Test that walk_files only returns non-ignored files."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            handler = IgnorePatternHandler(
                repo_root, custom_patterns=["test_*.py"]
            )

            # Create test directory structure
            (repo_root / "src").mkdir()
            (repo_root / "src" / "main.py").touch()
            (repo_root / "test_main.py").touch()
            (repo_root / ".venv").mkdir()
            (repo_root / ".venv" / "lib").mkdir()
            (repo_root / ".venv" / "lib" / "python.so").touch()

            files = handler.walk_files(repo_root)

            # Only non-ignored files should be returned
            file_names = [f.name for f in files]
            assert "main.py" in file_names
            assert "test_main.py" not in file_names
            assert "python.so" not in file_names

    def test_broken_symlinks_are_ignored(self):
        """Test that broken symlinks are handled gracefully."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            handler = IgnorePatternHandler(repo_root)

            # Create a real file and a broken symlink
            (repo_root / "real.py").touch()
            broken_link = repo_root / "broken_link"
            # On Windows, this might not work, so we skip if not supported
            try:
                broken_link.symlink_to("nonexistent")
                assert handler.should_ignore(broken_link)
            except (OSError, NotImplementedError):
                pytest.skip("Symlinks not supported on this OS")

    def test_pattern_matching_with_wildcards(self):
        """Test that wildcard patterns work correctly."""
        with TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            handler = IgnorePatternHandler(
                repo_root, custom_patterns=["*.log", "temp_*", "*_backup"]
            )

            (repo_root / "app.log").touch()
            (repo_root / "error.log").touch()
            (repo_root / "temp_file.txt").touch()
            (repo_root / "data_backup").mkdir()
            (repo_root / "data_backup" / "archive.tar").touch()
            (repo_root / "src.py").touch()

            assert handler.should_ignore(repo_root / "app.log")
            assert handler.should_ignore(repo_root / "error.log")
            assert handler.should_ignore(repo_root / "temp_file.txt")
            assert handler.should_ignore(repo_root / "data_backup")
            assert not handler.should_ignore(repo_root / "src.py")
