from pathlib import Path

from scripts.browser_video_remix.shot_splitter import build_shot_tasks


def test_build_shot_tasks_from_detected_boundaries(tmp_path: Path) -> None:
    source_video = tmp_path / "input" / "source.mp4"
    source_video.parent.mkdir(parents=True, exist_ok=True)
    source_video.write_bytes(b"video")

    tasks = build_shot_tasks(
        source_video=source_video,
        boundaries=[(0, 2400), (2400, 5100)],
        shots_dir=tmp_path / "work" / "shots",
    )

    assert [task.clip_id for task in tasks] == ["clip-0001", "clip-0002"]
    assert tasks[0].clip_path.as_posix().endswith("clip-0001.mp4")
    assert tasks[1].start_ms == 2400
