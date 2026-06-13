import os
import sys
from pathlib import Path

import pytest

# Ensure repository root is on sys.path so tests can import the `src` package.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES_DIR / "sample-repo"


@pytest.fixture
def sample_repo_path() -> Path:
    """Minimal TinyCalc repo for end-to-end comic generation tests."""
    return SAMPLE_REPO


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: live API test (set CODE_COMIC_RUN_LIVE=1 to enable)",
    )
