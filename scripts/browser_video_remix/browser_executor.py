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


def build_runninghub_payload(request: ClipExecutionRequest) -> dict[str, str]:
    return {
        "clip_id": request.clip_id,
        "video_path": str(request.clip_path),
        "reference_image_path": str(request.reference_image_path),
        "prompt": request.prompt,
        "resolution": f"{request.width}x{request.height}",
    }
