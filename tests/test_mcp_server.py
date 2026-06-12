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


def test_analyze_repo_missing_path_returns_structured_error(tmp_path):
    missing = tmp_path / "does-not-exist"
    out = mcp.analyze_repo(repo_path=str(missing))

    assert "error" in out
    assert out["error_type"] == "FileNotFoundError"
    assert out["operation"] == "analyze_repo"
    assert out["repo_path"] == str(missing)
    assert "hint" in out


def test_generate_comic_missing_path_returns_structured_error(tmp_path):
    missing = tmp_path / "does-not-exist"
    out = mcp.generate_comic(repo_path=str(missing))

    assert out["error_type"] == "FileNotFoundError"
    assert out["operation"] == "generate_comic"
    assert out.get("render_mode") == "html-mermaid"
    assert "log_note" in out


def test_generate_comic_returns_expected_keys(monkeypatch, tmp_path):
    # Fake Config class
    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.render_mode = "html-mermaid"
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
                "render_mode_used": "html-mermaid",
                "fallback": None,
                "html_file": str(Path(tmp_path) / f"{tmp_path.name}-comic.html"),
                "scenes": [{"title": "T1", "speech_bubble": "S1"}],
            }

    monkeypatch.setattr(mcp, "ComicRenderer", FakeRenderer)

    out = mcp.generate_comic(repo_path=str(tmp_path), context_mode="lightweight", render_mode="html-mermaid", output_dir=str(tmp_path))

    assert out.get("output_dir") == str(tmp_path)
    assert out.get("render_mode_used") == "html-mermaid"
    assert isinstance(out.get("scenes"), list)


def test_generate_comic_defaults_output_dir_to_repo_output(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    def fake_from_env(*, output_dir=None, context_mode=None, render_mode=None, repo_root=None, **kwargs):
        assert repo_root == str(repo_path)
        assert output_dir == str(repo_path / "output")
        return FakeConfig(output_dir=output_dir, context_mode=context_mode, render_mode=render_mode)

    class FakeConfig:
        def __init__(self, *args, **kwargs):
            self.render_mode = kwargs.get("render_mode", "html-mermaid")
            self.context_mode = kwargs.get("context_mode", "lightweight")
            self.output_dir = kwargs.get("output_dir", str(repo_path / "output"))
            self.ignore_patterns = []
            self.max_content_size_bytes = 500_000
            self.debug = False

    monkeypatch.setattr(mcp, "Config", type("C", (), {"from_env": staticmethod(fake_from_env)}))

    class FakeRenderer:
        def __init__(self, cfg):
            assert cfg.output_dir == str(repo_path / "output")

        def render(self, repo_path_arg):
            assert repo_path_arg == str(repo_path)
            return {
                "output_dir": str(repo_path / "output"),
                "render_mode_used": "html-mermaid",
                "fallback": None,
                "html_file": str(repo_path / "output" / f"{repo_path.name}-comic.html"),
                "scenes": [{"title": "T1", "speech_bubble": "S1"}],
            }

    monkeypatch.setattr(mcp, "ComicRenderer", FakeRenderer)

    out = mcp.generate_comic(repo_path=str(repo_path), context_mode="lightweight", render_mode="html-mermaid")

    assert out.get("output_dir") == str(repo_path / "output")
    assert out.get("render_mode_used") == "html-mermaid"
    assert isinstance(out.get("scenes"), list)
