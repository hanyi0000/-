from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
    ClipExecutionRequest,
    build_runninghub_payload,
)


def test_build_runninghub_payload_uses_clip_resolution() -> None:
    payload = build_runninghub_payload(
        ClipExecutionRequest(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
            width=1920,
            height=1080,
        )
    )

    assert payload["resolution"] == "1920x1080"
