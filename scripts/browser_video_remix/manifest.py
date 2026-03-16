from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClipTask:
    clip_id: str
    clip_path: Path
    frame_path: Path
    width: int
    height: int
    expected_resolution: str
    state: str


def build_clip_task(
    clip_id: str,
    clip_path: Path,
    frame_path: Path,
    width: int,
    height: int,
) -> ClipTask:
    return ClipTask(
        clip_id=clip_id,
        clip_path=clip_path,
        frame_path=frame_path,
        width=width,
        height=height,
        expected_resolution=f"{width}x{height}",
        state="pending",
    )
