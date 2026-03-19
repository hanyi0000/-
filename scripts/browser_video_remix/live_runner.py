from dataclasses import dataclass
from pathlib import Path

from .browser_executor import (
    ClipExecutionRequest,
    RunningHubTaskStatus,
    build_chatgpt_reference_job,
)
from .live_state import LiveClipState, load_live_state, save_live_state
from .paths import build_project_paths


@dataclass(frozen=True)
class LiveClipRequest:
    clip_id: str
    clip_path: Path
    frame_path: Path
    prompt: str
    state_path: Path
    rendered_output_path: Path
    width: int = 0
    height: int = 0


def run_single_clip_live_flow(
    request: LiveClipRequest,
    chatgpt_page: object,
    runninghub_page: object,
    chatgpt_adapter: object,
    runninghub_adapter: object,
) -> dict[str, str]:
    request.state_path.parent.mkdir(parents=True, exist_ok=True)
    existing_state = load_live_state(request.state_path) if request.state_path.exists() else None
    reference_image_path = (
        request.state_path.parent.parent / "chatgpt_refs" / f"{request.clip_id}.png"
    )
    reused_reference_image_path = (
        existing_state.reference_image_path
        if (
            existing_state is not None
            and existing_state.reference_image_path is not None
            and existing_state.reference_image_path.exists()
        )
        else None
    )
    resolved_reference_image_path = reused_reference_image_path or reference_image_path

    def build_result(task_id: str, result_reference_image_path: Path | None) -> dict[str, str]:
        return {
            "clip_id": request.clip_id,
            "task_id": task_id,
            "state_path": request.state_path.as_posix(),
            "reference_image_path": (
                ""
                if result_reference_image_path is None
                else result_reference_image_path.as_posix()
            ),
        }

    def persist_state(
        *,
        step: str,
        runninghub_task_id: str | None,
        pause_reason: object,
        reference_image_path: Path | None,
        last_screenshot_path: Path | None = None,
    ) -> None:
        save_live_state(
            request.state_path,
            LiveClipState(
                clip_id=request.clip_id,
                step=step,
                reference_image_path=reference_image_path,
                rendered_output_path=request.rendered_output_path,
                runninghub_task_id=runninghub_task_id,
                pause_reason=pause_reason,
                last_error=None,
                last_screenshot_path=last_screenshot_path,
            ),
        )

    def capture_runninghub_pause_artifacts() -> Path | None:
        snapshotter = getattr(runninghub_adapter, "capture_failure_snapshot", None)
        if not callable(snapshotter):
            return None
        pause_dir = build_project_paths(request.state_path.parents[2]).runninghub_pauses_dir
        clip_pause_dir = pause_dir / request.clip_id
        screenshot_path = clip_pause_dir / "pause.png"
        html_path = clip_pause_dir / "pause.html"
        summary_path = clip_pause_dir / "pause.json"
        snapshotter(
            runninghub_page,
            screenshot_path,
            html_path,
            summary_path,
        )
        return screenshot_path

    if reused_reference_image_path is None:
        chatgpt_request = build_chatgpt_reference_job(
            clip_id=request.clip_id,
            frame_path=request.frame_path,
            output_path=reference_image_path,
            prompt=request.prompt,
        )
        reference_result = chatgpt_adapter.submit_reference_generation(
            chatgpt_page,
            chatgpt_request,
        )
        if reference_result.pause_reason is not None:
            persist_state(
                step="paused",
                runninghub_task_id=None,
                pause_reason=reference_result.pause_reason,
                reference_image_path=None,
            )
            return build_result("", None)
        resolved_reference_image_path = reference_result.output_path

    runninghub_request = ClipExecutionRequest(
        clip_id=request.clip_id,
        clip_path=request.clip_path,
        reference_image_path=resolved_reference_image_path,
        prompt=request.prompt,
        width=request.width,
        height=request.height,
    )

    task_id = (
        existing_state.runninghub_task_id
        if existing_state is not None and existing_state.runninghub_task_id
        else None
    )
    if task_id is None:
        runninghub_result = runninghub_adapter.submit_render_job(
            runninghub_page,
            runninghub_request,
        )
        if runninghub_result.pause_reason is not None:
            screenshot_path = capture_runninghub_pause_artifacts()
            persist_state(
                step="paused",
                runninghub_task_id=runninghub_result.task_id,
                pause_reason=runninghub_result.pause_reason,
                reference_image_path=resolved_reference_image_path,
                last_screenshot_path=screenshot_path,
            )
            return build_result(
                "" if runninghub_result.task_id is None else str(runninghub_result.task_id),
                resolved_reference_image_path,
            )
        task_id = "" if runninghub_result.task_id is None else str(runninghub_result.task_id)
        persist_state(
            step="runninghub_submitted",
            runninghub_task_id=task_id or None,
            pause_reason=None,
            reference_image_path=resolved_reference_image_path,
        )
    else:
        ensure_session = getattr(runninghub_adapter, "ensure_session", None)
        if callable(ensure_session):
            session_result = ensure_session(runninghub_page)
            if session_result.pause_reason is not None:
                screenshot_path = capture_runninghub_pause_artifacts()
                persist_state(
                    step="paused",
                    runninghub_task_id=task_id,
                    pause_reason=session_result.pause_reason,
                    reference_image_path=resolved_reference_image_path,
                    last_screenshot_path=screenshot_path,
                )
                return build_result(task_id, resolved_reference_image_path)

    poll_result = runninghub_adapter.poll_render_status(runninghub_page, task_id)
    if poll_result.pause_reason is not None:
        screenshot_path = capture_runninghub_pause_artifacts()
        persist_state(
            step="paused",
            runninghub_task_id=task_id,
            pause_reason=poll_result.pause_reason,
            reference_image_path=resolved_reference_image_path,
            last_screenshot_path=screenshot_path,
        )
        return build_result(task_id, resolved_reference_image_path)
    persist_state(
        step="runninghub_polling",
        runninghub_task_id=task_id,
        pause_reason=None,
        reference_image_path=resolved_reference_image_path,
    )
    if poll_result.status == RunningHubTaskStatus.FAILED:
        persist_state(
            step="failed",
            runninghub_task_id=task_id,
            pause_reason=None,
            reference_image_path=resolved_reference_image_path,
        )
        return build_result(task_id, resolved_reference_image_path)
    if poll_result.status != RunningHubTaskStatus.DONE:
        return build_result(task_id, resolved_reference_image_path)

    download_result = runninghub_adapter.download_render_output(
        runninghub_page,
        request.rendered_output_path,
        task_id=task_id,
    )
    if download_result.pause_reason is not None:
        screenshot_path = capture_runninghub_pause_artifacts()
        persist_state(
            step="paused",
            runninghub_task_id=task_id,
            pause_reason=download_result.pause_reason,
            reference_image_path=resolved_reference_image_path,
            last_screenshot_path=screenshot_path,
        )
        return build_result(task_id, resolved_reference_image_path)

    persist_state(
        step="done",
        runninghub_task_id=task_id,
        pause_reason=None,
        reference_image_path=resolved_reference_image_path,
    )
    return build_result(task_id, resolved_reference_image_path)
