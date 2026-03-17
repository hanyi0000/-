from pathlib import Path

from scripts.browser_video_remix.manifest import ClipTask, load_manifest, save_manifest


def test_save_and_load_manifest_round_trip(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    tasks = [
        ClipTask(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            frame_path=Path("work/frames/clip-0001.png"),
            width=1920,
            height=1080,
            expected_resolution="1920x1080",
            state="pending",
        )
    ]

    save_manifest(manifest_path, tasks)
    loaded = load_manifest(manifest_path)

    assert loaded[0].clip_id == "clip-0001"
    assert loaded[0].clip_path.as_posix() == "work/clips/clip-0001.mp4"
