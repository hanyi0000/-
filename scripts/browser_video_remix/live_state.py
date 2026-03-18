import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PauseReason(str, Enum):
    LOGIN_REQUIRED = "login_required"
    CAPTCHA_REQUIRED = "captcha_required"
    SELECTOR_MISSING = "selector_missing"
    PAGE_CHANGED = "page_changed"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"


@dataclass(frozen=True)
class LiveClipState:
    clip_id: str
    step: str
    reference_image_path: Path | None
    rendered_output_path: Path | None
    runninghub_task_id: str | None
    pause_reason: PauseReason | None
    last_error: str | None
    last_screenshot_path: Path | None


def save_live_state(path: Path, state: LiveClipState) -> None:
    payload = {
        "clip_id": state.clip_id,
        "step": state.step,
        "reference_image_path": state.reference_image_path.as_posix() if state.reference_image_path else None,
        "rendered_output_path": state.rendered_output_path.as_posix() if state.rendered_output_path else None,
        "runninghub_task_id": state.runninghub_task_id,
        "pause_reason": state.pause_reason.value if state.pause_reason else None,
        "last_error": state.last_error,
        "last_screenshot_path": state.last_screenshot_path.as_posix() if state.last_screenshot_path else None,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_live_state(path: Path) -> LiveClipState:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return LiveClipState(
        clip_id=raw["clip_id"],
        step=raw["step"],
        reference_image_path=Path(raw["reference_image_path"]) if raw["reference_image_path"] else None,
        rendered_output_path=Path(raw["rendered_output_path"]) if raw["rendered_output_path"] else None,
        runninghub_task_id=raw["runninghub_task_id"],
        pause_reason=PauseReason(raw["pause_reason"]) if raw["pause_reason"] else None,
        last_error=raw["last_error"],
        last_screenshot_path=Path(raw["last_screenshot_path"]) if raw["last_screenshot_path"] else None,
    )
