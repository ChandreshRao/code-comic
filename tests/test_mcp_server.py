import os
from pathlib import Path

import pytest

from src import mcp_server as mcp


def test_resolve_repo_path_arg_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("CODE_COMIC_REPO_PATH", "/some/env/path")
    assert mcp._resolve_repo_path(str(tmp_path)) == str(tmp_path)
    monkeypatch.delenv("CODE_COMIC_REPO_PATH", raising=False)


def test_resolve_repo_path_env_over_cwd(tmp_path, monkeypatch):
    monkeypatch.setenv("CODE_COMIC_REPO_PATH", str(tmp_path))
    # change cwd to something else
    other = Path.cwd()
    monkeypatch.chdir(other)
    assert mcp._resolve_repo_path(None) == str(tmp_path)
    monkeypatch.delenv("CODE_COMIC_REPO_PATH", raising=False)


def test_generate_comic_returns_expected_keys(monkeypatch, tmp_path):
    # Fake Config class
    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.render_mode = "html"
            self.context_mode = "lightweight"
            self.output_dir = str(tmp_path)
            self.ignore_patterns = []
            self.max_content_size_bytes = 500_000
            self.debug = False

    monkeypatch.setattr(mcp, "Config", FakeConfig)

    # Fake renderer that returns a predictable payload
    class FakeRenderer:
        def __init__(self, cfg):
            pass

        def render(self, repo_path):
            return {
                "output_dir": str(tmp_path),
                "render_mode_used": "html",
                "fallback": None,
                "html_file": str(Path(tmp_path) / "comic.html"),
                "scenes": [{"title": "T1", "speech_bubble": "S1"}],
            }

    monkeypatch.setattr(mcp, "ComicRenderer", FakeRenderer)

    out = mcp.generate_comic(repo_path=str(tmp_path), context_mode="lightweight", render_mode="html", output_dir=str(tmp_path))

    assert out.get("output_dir") == str(tmp_path)
    assert out.get("render_mode_used") == "html"
    assert isinstance(out.get("scenes"), list)
