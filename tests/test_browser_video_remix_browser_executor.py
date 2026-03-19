from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
    ClipExecutionRequest,
    build_chatgpt_reference_job,
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


def test_build_chatgpt_reference_job_wraps_prompt_for_image_editing() -> None:
    request = build_chatgpt_reference_job(
        clip_id="clip-0001",
        frame_path=Path("work/frames/clip-0001.png"),
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    assert "Edit the attached image." in request.prompt
    assert "Return only the edited image." in request.prompt
    assert "replace actor_a with jett" in request.prompt
