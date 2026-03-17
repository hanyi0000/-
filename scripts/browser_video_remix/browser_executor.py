from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClipExecutionRequest:
    clip_id: str
    clip_path: Path
    reference_image_path: Path
    prompt: str
    width: int
    height: int


@dataclass(frozen=True)
class ChatGptReferenceRequest:
    clip_id: str
    frame_path: Path
    output_path: Path
    prompt: str


def build_runninghub_payload(request: ClipExecutionRequest) -> dict[str, str]:
    return {
        "clip_id": request.clip_id,
        "video_path": str(request.clip_path),
        "reference_image_path": str(request.reference_image_path),
        "prompt": request.prompt,
        "resolution": f"{request.width}x{request.height}",
    }


def build_chatgpt_reference_job(
    clip_id: str,
    frame_path: Path,
    output_path: Path,
    prompt: str,
) -> ChatGptReferenceRequest:
    return ChatGptReferenceRequest(
        clip_id=clip_id,
        frame_path=frame_path,
        output_path=output_path,
        prompt=prompt,
    )
