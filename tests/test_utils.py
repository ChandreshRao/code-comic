from datetime import datetime
from pathlib import Path

from src.utils import default_output_dir, timestamped_output_dir_name


def test_timestamped_output_dir_name():
    moment = datetime(2026, 6, 13, 15, 56, 30)
    assert timestamped_output_dir_name(now=moment) == "code-comic-20260613-155630"


def test_default_output_dir():
    moment = datetime(2026, 6, 13, 15, 56, 30)
    repo = Path("/tmp/my-repo")
    assert default_output_dir(str(repo), now=moment) == str(repo / "code-comic-20260613-155630")
