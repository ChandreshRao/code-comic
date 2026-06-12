from pathlib import Path

from src.analyzer import analyze_repository


def test_analyze_repository_identifies_python_files(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("Example repo")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')")

    metadata = analyze_repository(str(tmp_path))

    assert metadata["total_files"] == 2
    assert "README.md" in metadata["top_level"]
    assert ".py" in metadata["file_counts"]
    assert metadata["package_files"] == []
