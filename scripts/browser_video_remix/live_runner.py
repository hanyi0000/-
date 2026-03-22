import json
from dataclasses import dataclass, field
from pathlib import Path

from .browser_executor import (
    ClipExecutionRequest,
    RunningHubTaskStatus,
    build_chatgpt_reference_job,
    build_person_reference_job,
)
from .live_state import LiveClipState, PauseReason, load_live_state, save_live_state
from .paths import build_project_paths
from .replacement_audit import plan_retry_action


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
    person_frame_paths: dict[str, Path] = field(default_factory=dict)
    max_retry_attempts: int = 3


def run_single_clip_live_flow(
    request: LiveClipRequest,
    chatgpt_page: object,
    runninghub_page: object,
    chatgpt_adapter: object,
    runninghub_adapter: object,
    audit_runner: object | None = None,
) -> dict[str, str]:
    request.state_path.parent.mkdir(parents=True, exist_ok=True)
    existing_state = load_live_state(request.state_path) if request.state_path.exists() else None
    reference_image_path = (
        request.state_path.parent.parent / "chatgpt_refs" / f"{request.clip_id}.png"
    )
    person_reference_images = _existing_person_reference_images(existing_state)
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
    retry_count = 0 if existing_state is None else existing_state.retry_count

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
        person_reference_images: dict[str, Path] | None = None,
        retry_count: int = 0,
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
                person_reference_images={} if person_reference_images is None else dict(person_reference_images),
                retry_count=retry_count,
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

    def capture_chatgpt_pause_artifacts() -> Path | None:
        snapshotter = getattr(chatgpt_adapter, "capture_snapshot", None)
        if not callable(snapshotter):
            return None
        context = getattr(chatgpt_page, "context", None)
        if callable(context):
            context = context()
        if context is None:
            return None
        clip_pause_dir = request.state_path.parents[2] / "logs" / "chatgpt-pauses" / request.clip_id
        screenshot_path = clip_pause_dir / "pause.png"
        html_path = clip_pause_dir / "pause.html"
        snapshotter(
            context=context,
            screenshot_path=screenshot_path,
            html_path=html_path,
        )
        return screenshot_path

    task_id = (
        existing_state.runninghub_task_id
        if existing_state is not None and existing_state.runninghub_task_id
        else None
    )
    while True:
        if reused_reference_image_path is None and not person_reference_images:
            reference_result, person_reference_images = _generate_reference_images(
                request=request,
                chatgpt_page=chatgpt_page,
                chatgpt_adapter=chatgpt_adapter,
                default_reference_image_path=reference_image_path,
            )
            if reference_result.pause_reason is not None:
                screenshot_path = capture_chatgpt_pause_artifacts()
                persist_state(
                    step="paused",
                    runninghub_task_id=None,
                    pause_reason=reference_result.pause_reason,
                    reference_image_path=None,
                    retry_count=retry_count,
                    last_screenshot_path=screenshot_path,
                )
                return build_result("", None)
            resolved_reference_image_path = reference_result.output_path

        if person_reference_images and resolved_reference_image_path is None:
            resolved_reference_image_path = next(iter(person_reference_images.values()))

        reference_audit_result = _run_reference_audit(
            audit_runner,
            clip_id=request.clip_id,
            person_reference_images=person_reference_images,
        )
        if reference_audit_result is not None and reference_audit_result.status == "retry":
            should_retry, retry_count, should_regenerate = _handle_audit_retry(
                request=request,
                clip_id=request.clip_id,
                retry_count=retry_count,
                task_id=None,
                reference_image_path=resolved_reference_image_path,
                person_reference_images=person_reference_images,
                audit_result=reference_audit_result,
                persist_state=persist_state,
                notification_dir=build_project_paths(request.state_path.parents[2]).logs_notifications_dir,
            )
            if not should_retry:
                return build_result("", resolved_reference_image_path)
            task_id = None
            if should_regenerate:
                reused_reference_image_path = None
                resolved_reference_image_path = None
                person_reference_images = {}
            continue

        runninghub_request = ClipExecutionRequest(
            clip_id=request.clip_id,
            clip_path=request.clip_path,
            reference_image_path=resolved_reference_image_path,
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            person_reference_images=person_reference_images,
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
                    person_reference_images=person_reference_images,
                    retry_count=retry_count,
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
                person_reference_images=person_reference_images,
                retry_count=retry_count,
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
                        person_reference_images=person_reference_images,
                        retry_count=retry_count,
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
                person_reference_images=person_reference_images,
                retry_count=retry_count,
                last_screenshot_path=screenshot_path,
            )
            return build_result(task_id, resolved_reference_image_path)
        persist_state(
            step="runninghub_polling",
            runninghub_task_id=task_id,
            pause_reason=None,
            reference_image_path=resolved_reference_image_path,
            person_reference_images=person_reference_images,
            retry_count=retry_count,
        )
        if poll_result.status == RunningHubTaskStatus.FAILED:
            persist_state(
                step="failed",
                runninghub_task_id=task_id,
                pause_reason=None,
                reference_image_path=resolved_reference_image_path,
                person_reference_images=person_reference_images,
                retry_count=retry_count,
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
                person_reference_images=person_reference_images,
                retry_count=retry_count,
                last_screenshot_path=screenshot_path,
            )
            return build_result(task_id, resolved_reference_image_path)

        render_audit_result = _run_render_audit(
            audit_runner,
            clip_id=request.clip_id,
            rendered_output_path=request.rendered_output_path,
            person_reference_images=person_reference_images,
        )
        if render_audit_result is not None and render_audit_result.status == "retry":
            should_retry, retry_count, should_regenerate = _handle_audit_retry(
                request=request,
                clip_id=request.clip_id,
                retry_count=retry_count,
                task_id=task_id,
                reference_image_path=resolved_reference_image_path,
                person_reference_images=person_reference_images,
                audit_result=render_audit_result,
                persist_state=persist_state,
                notification_dir=build_project_paths(request.state_path.parents[2]).logs_notifications_dir,
            )
            if not should_retry:
                return build_result(task_id, resolved_reference_image_path)
            task_id = None
            if should_regenerate:
                reused_reference_image_path = None
                resolved_reference_image_path = None
                person_reference_images = {}
            continue

        persist_state(
            step="done",
            runninghub_task_id=task_id,
            pause_reason=None,
            reference_image_path=resolved_reference_image_path,
            person_reference_images=person_reference_images,
            retry_count=retry_count,
        )
        return build_result(task_id, resolved_reference_image_path)


def _existing_person_reference_images(existing_state: LiveClipState | None) -> dict[str, Path]:
    if existing_state is None:
        return {}
    return {
        person_id: image_path
        for person_id, image_path in existing_state.person_reference_images.items()
        if image_path.exists()
    }


def _generate_reference_images(
    *,
    request: LiveClipRequest,
    chatgpt_page: object,
    chatgpt_adapter: object,
    default_reference_image_path: Path,
) -> tuple[object, dict[str, Path]]:
    person_reference_images: dict[str, Path] = {}
    if request.person_frame_paths:
        last_result = None
        for source_person_id, frame_path in request.person_frame_paths.items():
            output_path = (
                request.state_path.parent.parent / "chatgpt_refs" / f"{request.clip_id}_{source_person_id}.png"
            )
            chatgpt_request = build_person_reference_job(
                clip_id=request.clip_id,
                source_person_id=source_person_id,
                frame_path=frame_path,
                output_path=output_path,
                prompt=request.prompt,
            )
            last_result = chatgpt_adapter.submit_reference_generation(
                chatgpt_page,
                chatgpt_request,
            )
            if last_result.pause_reason is not None:
                return last_result, person_reference_images
            person_reference_images[source_person_id] = last_result.output_path
        return last_result, person_reference_images

    chatgpt_request = build_chatgpt_reference_job(
        clip_id=request.clip_id,
        frame_path=request.frame_path,
        output_path=default_reference_image_path,
        prompt=request.prompt,
    )
    reference_result = chatgpt_adapter.submit_reference_generation(
        chatgpt_page,
        chatgpt_request,
    )
    return reference_result, person_reference_images


def _run_reference_audit(
    audit_runner: object | None,
    *,
    clip_id: str,
    person_reference_images: dict[str, Path],
) -> object | None:
    if audit_runner is None:
        return None
    runner = getattr(audit_runner, "run_reference_audit", None)
    if not callable(runner):
        return None
    return runner(
        clip_id=clip_id,
        person_reference_images=person_reference_images,
    )


def _run_render_audit(
    audit_runner: object | None,
    *,
    clip_id: str,
    rendered_output_path: Path,
    person_reference_images: dict[str, Path],
) -> object | None:
    if audit_runner is None:
        return None
    runner = getattr(audit_runner, "run_render_audit", None)
    if not callable(runner):
        return None
    return runner(
        clip_id=clip_id,
        rendered_output_path=rendered_output_path,
        person_reference_images=person_reference_images,
    )


def _handle_audit_retry(
    *,
    request: LiveClipRequest,
    clip_id: str,
    retry_count: int,
    task_id: str | None,
    reference_image_path: Path | None,
    person_reference_images: dict[str, Path],
    audit_result: object,
    persist_state: object,
    notification_dir: Path,
) -> tuple[bool, int, bool]:
    next_retry_count = retry_count + 1
    action = plan_retry_action(
        audit_result,
        attempt=next_retry_count,
        max_attempts=request.max_retry_attempts,
    )
    if action == "pause_and_notify":
        _write_notification(
            notification_dir=notification_dir,
            clip_id=clip_id,
            task_id=task_id,
            retry_count=next_retry_count,
            audit_result=audit_result,
            action=action,
        )
        persist_state(
            step="paused",
            runninghub_task_id=task_id,
            pause_reason=PauseReason.MANUAL_CONFIRMATION_REQUIRED,
            reference_image_path=reference_image_path,
            person_reference_images=person_reference_images,
            retry_count=next_retry_count,
        )
        return (False, next_retry_count, False)

    persist_state(
        step="references_ready",
        runninghub_task_id=None,
        pause_reason=None,
        reference_image_path=reference_image_path,
        person_reference_images=person_reference_images,
        retry_count=next_retry_count,
    )
    return (True, next_retry_count, action == "choose_alternate_keyframe")


def _write_notification(
    *,
    notification_dir: Path,
    clip_id: str,
    task_id: str | None,
    retry_count: int,
    audit_result: object,
    action: str,
) -> None:
    notification_dir.mkdir(parents=True, exist_ok=True)
    notification_path = notification_dir / f"{clip_id}.json"
    notification_path.write_text(
        json.dumps(
            {
                "clip_id": clip_id,
                "task_id": task_id,
                "retry_count": retry_count,
                "status": getattr(audit_result, "status", ""),
                "finding_type": getattr(audit_result, "finding_type", ""),
                "confidence": getattr(audit_result, "confidence", 0.0),
                "action": action,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
