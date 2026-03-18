from pathlib import Path

from scripts.browser_video_remix.cli import (
    build_chatgpt_snapshot_request,
    build_live_run_request,
)


def test_build_live_run_request_points_to_state_and_downloads(tmp_path: Path) -> None:
    request = build_live_run_request(
        project_dir=tmp_path / "projects" / "demo",
        clip_id="clip-0001",
    )

    assert request.clip_id == "clip-0001"
    assert request.state_path.name == "clip-0001.json"
    assert request.downloads_dir.name == "downloads"


def test_build_chatgpt_snapshot_request_points_to_log_artifacts(tmp_path: Path) -> None:
    request = build_chatgpt_snapshot_request(
        project_dir=tmp_path / "projects" / "demo",
        start_url="https://chatgpt.com/g/test",
    )

    assert request.url == "https://chatgpt.com/g/test"
    assert request.screenshot_path.name == "chatgpt-page.png"
    assert request.html_path.name == "chatgpt-page.html"
