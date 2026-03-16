from pathlib import Path

from scripts.browser_video_remix.cli import build_project_paths


def test_build_project_paths_returns_expected_structure(tmp_path: Path) -> None:
    result = build_project_paths(tmp_path / "projects" / "demo")

    assert result.project_dir == tmp_path / "projects" / "demo"
    assert result.input_dir.name == "input"
    assert result.work_clips_dir.name == "clips"
    assert result.output_rendered_dir.name == "rendered"
