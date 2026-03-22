from pathlib import Path

from scripts.browser_video_remix.cli import build_project_paths, build_single_clip_flow_summary


def test_build_project_paths_returns_expected_structure(tmp_path: Path) -> None:
    result = build_project_paths(tmp_path / "projects" / "demo")

    assert result.project_dir == tmp_path / "projects" / "demo"
    assert result.input_dir.name == "input"
    assert result.work_clips_dir.name == "clips"
    assert result.output_rendered_dir.name == "rendered"


def test_cli_reexports_single_clip_flow_summary(tmp_path: Path) -> None:
    summary = build_single_clip_flow_summary(
        project_dir=tmp_path / "projects" / "demo",
        clip_id="clip-0001",
    )

    assert summary["clip_id"] == "clip-0001"
