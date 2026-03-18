from pathlib import Path

from scripts.browser_video_remix.live_state import (
    LiveClipState,
    PauseReason,
    load_live_state,
    save_live_state,
)


def test_save_and_load_live_state_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "clip-0001.json"
    state = LiveClipState(
        clip_id="clip-0001",
        step="reference_saved",
        reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
        rendered_output_path=None,
        runninghub_task_id=None,
        pause_reason=PauseReason.LOGIN_REQUIRED,
        last_error=None,
        last_screenshot_path=Path("work/screenshots/clip-0001-login.png"),
    )

    save_live_state(state_path, state)
    loaded = load_live_state(state_path)

    assert loaded.step == "reference_saved"
    assert loaded.pause_reason == PauseReason.LOGIN_REQUIRED
    assert loaded.reference_image_path.as_posix() == "work/chatgpt_refs/clip-0001.png"
