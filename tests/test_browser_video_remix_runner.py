from pathlib import Path

from scripts.browser_video_remix.runner import plan_batch_run


def test_plan_batch_run_returns_clip_count(tmp_path: Path) -> None:
    result = plan_batch_run(
        project_dir=tmp_path / "projects" / "demo",
        manifest_entries=["clip-0001", "clip-0002"],
        dry_run=True,
    )

    assert result.clip_count == 2
    assert result.dry_run is True
