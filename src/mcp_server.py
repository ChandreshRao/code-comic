from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - graceful when mcp not installed during tests
    FastMCP = None

from .analyzer import analyze_repository
from .config import Config
from .log_setup import get_logger, setup_logging
from .renderer import ComicRenderer
from .utils import default_output_dir

logger = get_logger("mcp_server")


def _resolve_repo_path(repo_path: Optional[str]) -> str:
    resolved = repo_path or os.environ.get("CODE_COMIC_REPO_PATH") or os.getcwd()
    logger.debug(
        "Resolved repo path: %s (arg=%r, env=%r, cwd=%r)",
        resolved,
        repo_path,
        os.environ.get("CODE_COMIC_REPO_PATH"),
        os.getcwd(),
    )
    return resolved


def _validate_repo_path(repo: str) -> Path:
    path = Path(repo).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {path} "
            f"(resolved from {repo!r}; cwd={os.getcwd()!r})"
        )
    if not path.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {path}")
    return path.resolve()


def _error_hint(exc: BaseException) -> str | None:
    if isinstance(exc, FileNotFoundError):
        return (
            "Pass a valid absolute repo_path, set CODE_COMIC_REPO_PATH, or run the MCP "
            "server with cwd set to the target repository."
        )
    if isinstance(exc, NotADirectoryError):
        return "repo_path must point to a directory, not a file."
    if isinstance(exc, PermissionError):
        return "Check read/write permissions for the repository and output directory."
    if isinstance(exc, ValueError):
        return "Check render_mode, context_mode, and other tool parameters."
    if isinstance(exc, RuntimeError):
        return "Often caused by missing API keys or upstream LLM/image API failures. Check stderr logs."
    return None


def _error_response(
    exc: BaseException,
    *,
    repo: str,
    operation: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    hint = _error_hint(exc)
    logger.error("%s failed for repo=%s: %s: %s", operation, repo, type(exc).__name__, exc)
    logger.debug("Traceback for %s:\n%s", operation, traceback.format_exc())

    payload: Dict[str, Any] = {
        "error": str(exc),
        "error_type": type(exc).__name__,
        "repo_path": repo,
        "operation": operation,
    }
    if hint:
        payload["hint"] = hint
    if extra:
        payload.update(extra)
    if os.environ.get("CODE_COMIC_DEBUG", "").lower() in ("1", "true", "yes"):
        payload["traceback"] = traceback.format_exc()
    payload["log_note"] = "Full details are written to the MCP server stderr log."
    return payload


def _log_config_summary(cfg: Any, repo: str) -> None:
    logger.info(
        "Starting with repo=%s render_mode=%s context_mode=%s output_dir=%s",
        repo,
        getattr(cfg, "render_mode", "?"),
        getattr(cfg, "context_mode", "?"),
        getattr(cfg, "output_dir", "?"),
    )
    logger.debug(
        "Config details: llm_provider=%s llm_models=%s llm_key_set=%s "
        "image_provider=%s image_models=%s image_key_set=%s ignore_patterns=%s debug=%s",
        getattr(cfg, "llm_provider_resolved", getattr(cfg, "llm_provider", None)),
        getattr(cfg, "llm_models_resolved", getattr(cfg, "llm_models", None)),
        bool(getattr(cfg, "llm_api_key", None)),
        getattr(cfg, "image_provider_resolved", getattr(cfg, "image_provider", None)),
        getattr(cfg, "image_models_resolved", getattr(cfg, "image_models", None)),
        bool(getattr(cfg, "image_api_key", None)),
        getattr(cfg, "ignore_patterns", None),
        getattr(cfg, "debug", False),
    )


def _build_config(
    *,
    repo: str,
    render_mode: str,
    context_mode: str,
    output_dir: str,
) -> Any:
    try:
        cfg = Config.from_env(
            render_mode=render_mode,
            context_mode=context_mode,
            output_dir=output_dir,
            repo_root=repo,
        )
        logger.debug("Loaded configuration via Config.from_env")
        return cfg
    except Exception as exc:
        logger.warning(
            "Config.from_env failed (%s: %s); using lightweight fallback config",
            type(exc).__name__,
            exc,
        )

        class _FallbackConfig:
            def __init__(self) -> None:
                self.render_mode = render_mode
                self.context_mode = context_mode
                self.output_dir = output_dir
                self.ignore_patterns: list[str] = []
                self.max_content_size_bytes = 500_000
                self.debug = os.environ.get("CODE_COMIC_DEBUG", "").lower() in ("1", "true", "yes")

        return _FallbackConfig()


def analyze_repo(repo_path: Optional[str] = None, context_mode: str = "lightweight") -> Dict[str, Any]:
    """Analyze repository metadata.

    Read-only tool: calls `analyze_repository` and returns the resulting dict.
    """
    repo = _resolve_repo_path(repo_path)
    logger.info("analyze_repo called (repo=%s, context_mode=%s)", repo, context_mode)

    try:
        validated = _validate_repo_path(repo)
        repo = str(validated)
        metadata = analyze_repository(repo, context_mode=context_mode)
        logger.info(
            "analyze_repo succeeded (repo=%s, files=%s, context_mode=%s)",
            repo,
            metadata.get("total_files"),
            metadata.get("context_mode"),
        )
        return {"repo_path": repo, "metadata": metadata}
    except Exception as exc:
        return _error_response(exc, repo=repo, operation="analyze_repo")


def generate_comic(
    repo_path: Optional[str] = None,
    context_mode: str = "lightweight",
    render_mode: str = "html-mermaid",
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a comic using existing renderer.

    render_mode: 'html-mermaid' (Mermaid diagrams, default) or 'html-image'
    (PNG panels in images/ referenced from HTML; auto-fallback to html-mermaid on failure).

    Returns a summary JSON containing output_dir, render_mode_used, fallback, scenes, and html_file when present.
    """
    repo = _resolve_repo_path(repo_path)
    if output_dir is None:
        output_dir = default_output_dir(repo)

    logger.info(
        "generate_comic called (repo=%s, context_mode=%s, render_mode=%s, output_dir=%s)",
        repo,
        context_mode,
        render_mode,
        output_dir,
    )

    try:
        validated = _validate_repo_path(repo)
        repo = str(validated)

        cfg = _build_config(
            repo=repo,
            render_mode=render_mode,
            context_mode=context_mode,
            output_dir=output_dir,
        )
        cfg.output_dir = output_dir
        _log_config_summary(cfg, repo)

        renderer = ComicRenderer(cfg)
        logger.info("Rendering comic for repo=%s", repo)
        result = renderer.render(repo)

        scenes = [
            {"title": s.get("title"), "description": s.get("speech_bubble") or s.get("panel_text")}
            for s in result.get("scenes", [])
        ]

        if result.get("fallback"):
            logger.warning(
                "generate_comic used fallback=%s (requested render_mode=%s, used=%s)",
                result.get("fallback"),
                render_mode,
                result.get("render_mode_used"),
            )
        else:
            logger.info(
                "generate_comic succeeded (output_dir=%s, render_mode_used=%s, html_file=%s)",
                result.get("output_dir"),
                result.get("render_mode_used"),
                result.get("html_file"),
            )

        return {
            "output_dir": result.get("output_dir"),
            "render_mode_used": result.get("render_mode_used"),
            "fallback": result.get("fallback"),
            "html_file": result.get("html_file"),
            "scenes": scenes,
        }
    except Exception as exc:
        return _error_response(
            exc,
            repo=repo,
            operation="generate_comic",
            extra={"output_dir": output_dir, "render_mode": render_mode, "context_mode": context_mode},
        )


def main() -> None:
    setup_logging()
    logger.info("Starting code-comic MCP server (pid=%s, cwd=%s)", os.getpid(), os.getcwd())
    logger.debug(
        "Environment: CODE_COMIC_REPO_PATH=%r CODE_COMIC_LOG_LEVEL=%r CODE_COMIC_DEBUG=%r",
        os.environ.get("CODE_COMIC_REPO_PATH"),
        os.environ.get("CODE_COMIC_LOG_LEVEL"),
        os.environ.get("CODE_COMIC_DEBUG"),
    )

    if FastMCP is None:
        logger.error("FastMCP is not installed. Install with 'mcp[cli]' to run the MCP server.")
        return

    mcp = FastMCP()

    mcp.tool("analyze_repo")(analyze_repo)
    mcp.tool("generate_comic")(generate_comic)

    logger.info("Registered MCP tools: analyze_repo, generate_comic")
    mcp.run()


if __name__ == "__main__":
    main()
