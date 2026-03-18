from dataclasses import dataclass
from pathlib import Path

from .browser_executor import ClipExecutionRequest, build_chatgpt_reference_job
from .live_state import LiveClipState, save_live_state


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
    reference_image_path = (
        request.state_path.parent.parent / "chatgpt_refs" / f"{request.clip_id}.png"
    )

    chatgpt_request = build_chatgpt_reference_job(
        clip_id=request.clip_id,
        frame_path=request.frame_path,
        output_path=reference_image_path,
        prompt=request.prompt,
    )
    runninghub_request = ClipExecutionRequest(
        clip_id=request.clip_id,
        clip_path=request.clip_path,
        reference_image_path=reference_image_path,
        prompt=request.prompt,
        width=request.width,
        height=request.height,
    )

    reference_result = chatgpt_adapter.submit_reference_generation(
        chatgpt_page,
        chatgpt_request,
    )
    runninghub_result = runninghub_adapter.submit_render_job(
        runninghub_page,
        runninghub_request,
    )

    save_live_state(
        request.state_path,
        LiveClipState(
            clip_id=request.clip_id,
            step=runninghub_result.status,
            reference_image_path=reference_result.output_path,
            rendered_output_path=request.rendered_output_path,
            runninghub_task_id=runninghub_result.task_id,
            pause_reason=runninghub_result.pause_reason,
            last_error=None,
            last_screenshot_path=None,
        ),
    )

    return {
        "clip_id": request.clip_id,
        "task_id": str(runninghub_result.task_id),
        "state_path": request.state_path.as_posix(),
        "reference_image_path": reference_result.output_path.as_posix(),
    }
