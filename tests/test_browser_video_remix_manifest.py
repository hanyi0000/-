from pathlib import Path

from scripts.browser_video_remix.manifest import build_clip_task


def test_build_clip_task_sets_initial_state() -> None:
    task = build_clip_task(
        clip_id="clip-0001",
        clip_path=Path("work/clips/clip-0001.mp4"),
        frame_path=Path("work/frames/clip-0001.png"),
        width=1920,
        height=1080,
    )

    assert task.state == "pending"
    assert task.expected_resolution == "1920x1080"
