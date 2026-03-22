from pathlib import Path

from scripts.browser_video_remix.media import build_frame_command, build_split_command


def test_build_split_command_uses_segment_output_pattern() -> None:
    command = build_split_command(
        source_video=Path("input/source.mp4"),
        output_pattern=Path("work/clips/clip-%04d.mp4"),
        seconds=2,
    )

    assert command[:2] == ["ffmpeg", "-i"]
    assert "-f" in command
    assert "segment" in command
    assert "work/clips/clip-%04d.mp4" in command


def test_build_frame_command_targets_single_output_image() -> None:
    command = build_frame_command(
        clip_path=Path("work/clips/clip-0001.mp4"),
        frame_path=Path("work/frames/clip-0001.png"),
    )

    assert command[:2] == ["ffmpeg", "-i"]
    assert "-frames:v" in command
    assert "1" in command
