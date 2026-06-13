from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False
_ROOT_LOGGER = "code_comic"


def setup_logging(*, debug: bool | None = None, level: str | None = None) -> logging.Logger:
    """Configure code-comic logging to stderr (safe for MCP stdio servers)."""
    global _CONFIGURED

    logger = logging.getLogger(_ROOT_LOGGER)

    if _CONFIGURED and debug is None and level is None:
        return logger

    level_name = (level or os.environ.get("CODE_COMIC_LOG_LEVEL", "")).upper()
    if not level_name:
        if debug is None:
            debug = os.environ.get("CODE_COMIC_DEBUG", "").lower() in ("1", "true", "yes")
        level_name = "DEBUG" if debug else "INFO"

    numeric_level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger(_ROOT_LOGGER)
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)
    root.propagate = False

    _CONFIGURED = True
    return root


def get_logger(name: str | None = None) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    if name is None or name == _ROOT_LOGGER:
        return logging.getLogger(_ROOT_LOGGER)
    if not name.startswith(f"{_ROOT_LOGGER}."):
        name = f"{_ROOT_LOGGER}.{name.removeprefix(_ROOT_LOGGER + '.')}"
    return logging.getLogger(name)
