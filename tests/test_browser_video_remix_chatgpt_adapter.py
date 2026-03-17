from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
    ChatGptReferenceRequest,
    build_chatgpt_reference_job,
)


def test_build_chatgpt_reference_job_tracks_input_and_output_paths() -> None:
    job = build_chatgpt_reference_job(
        clip_id="clip-0001",
        frame_path=Path("work/frames/clip-0001.png"),
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    assert job.clip_id == "clip-0001"
    assert job.output_path.as_posix() == "work/chatgpt_refs/clip-0001.png"
