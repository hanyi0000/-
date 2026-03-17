from pathlib import Path

from scripts.browser_video_remix.runner import plan_prepare_run


def test_plan_prepare_run_returns_expected_artifact_paths(tmp_path: Path) -> None:
    result = plan_prepare_run(
        project_dir=tmp_path / "projects" / "demo",
        clip_count=3,
    )

    assert result.clip_count == 3
    assert result.manifest_path.name == "manifest.json"
    assert result.frames_dir.name == "frames"
