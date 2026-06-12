from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - graceful when mcp not installed during tests
    FastMCP = None

from .analyzer import analyze_repository
from .renderer import ComicRenderer
from .config import Config


def _resolve_repo_path(repo_path: Optional[str]) -> str:
    return repo_path or os.environ.get("CODE_COMIC_REPO_PATH") or os.getcwd()


def analyze_repo(repo_path: Optional[str] = None, context_mode: str = "lightweight") -> Dict[str, Any]:
    """Analyze repository metadata.

    Read-only tool: calls `analyze_repository` and returns the resulting dict.
    """
    repo = _resolve_repo_path(repo_path)
    try:
        metadata = analyze_repository(repo, context_mode=context_mode)
        return {"repo_path": repo, "metadata": metadata}
    except Exception as exc:
        return {"error": str(exc)}


def generate_comic(
    repo_path: Optional[str] = None,
    context_mode: str = "lightweight",
    render_mode: str = "html",
    output_dir: str = "output",
) -> Dict[str, Any]:
    """Generate a comic using existing renderer.

    Returns a summary JSON containing output_dir, render_mode_used, fallback, scenes, and html_file when present.
    """
    repo = _resolve_repo_path(repo_path)
    try:
        # Build config from environment and overrides where supported
        try:
            cfg = Config.from_env(render_mode=render_mode, context_mode=context_mode)
        except Exception:
            # Lightweight fallback config if Config.from_env is not available
            class _C:  # type: ignore
                pass

            cfg = _C()
            cfg.render_mode = render_mode
            cfg.context_mode = context_mode
            cfg.output_dir = output_dir
            cfg.ignore_patterns = []
            cfg.max_content_size_bytes = 500_000
            cfg.debug = False

        # Ensure output_dir takes provided value
        cfg.output_dir = output_dir

        renderer = ComicRenderer(cfg)
        result = renderer.render(repo)

        scenes = [
            {"title": s.get("title"), "description": s.get("speech_bubble") or s.get("panel_text")} for s in result.get("scenes", [])
        ]

        return {
            "output_dir": result.get("output_dir"),
            "render_mode_used": result.get("render_mode_used"),
            "fallback": result.get("fallback"),
            "html_file": result.get("html_file"),
            "scenes": scenes,
        }
    except Exception as exc:
        return {"error": str(exc)}


def main() -> None:
    if FastMCP is None:
        print("FastMCP is not installed. Install with 'mcp[cli]' to run the MCP server.")
        return

    mcp = FastMCP()

    # Register two thin tools that call into existing code paths
    mcp.tool("analyze_repo")(analyze_repo)
    mcp.tool("generate_comic")(generate_comic)

    mcp.run()


if __name__ == "__main__":
    main()
