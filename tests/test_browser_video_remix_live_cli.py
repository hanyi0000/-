from pathlib import Path

from scripts.browser_video_remix.cli import build_live_run_request


def test_build_live_run_request_points_to_state_and_downloads(tmp_path: Path) -> None:
    request = build_live_run_request(
        project_dir=tmp_path / "projects" / "demo",
        clip_id="clip-0001",
    )

    assert request.clip_id == "clip-0001"
    assert request.state_path.name == "clip-0001.json"
    assert request.downloads_dir.name == "downloads"
