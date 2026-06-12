import logging

import pytest

from src import log_setup


@pytest.fixture(autouse=True)
def reset_logging():
    log_setup._CONFIGURED = False
    root = logging.getLogger("code_comic")
    root.handlers.clear()
    yield
    log_setup._CONFIGURED = False
    root.handlers.clear()


def test_setup_logging_defaults_to_info(capsys):
    logger = log_setup.setup_logging()
    logger.info("hello-info")
    logger.debug("hello-debug")

    captured = capsys.readouterr()
    assert "hello-info" in captured.err
    assert "hello-debug" not in captured.err
    assert captured.out == ""


def test_setup_logging_debug_env(monkeypatch, capsys):
    monkeypatch.setenv("CODE_COMIC_DEBUG", "1")
    logger = log_setup.setup_logging()
    logger.debug("verbose")

    captured = capsys.readouterr()
    assert "verbose" in captured.err


def test_setup_logging_level_env(monkeypatch, capsys):
    monkeypatch.setenv("CODE_COMIC_LOG_LEVEL", "WARNING")
    logger = log_setup.setup_logging()
    logger.info("hidden")
    logger.warning("shown")

    captured = capsys.readouterr()
    assert "hidden" not in captured.err
    assert "shown" in captured.err
