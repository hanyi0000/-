import json
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


def save_manifest(path: Path, tasks: list[ClipTask]) -> None:
    payload = [
        {
            "clip_id": task.clip_id,
            "clip_path": str(task.clip_path),
            "frame_path": str(task.frame_path),
            "width": task.width,
            "height": task.height,
            "expected_resolution": task.expected_resolution,
            "state": task.state,
        }
        for task in tasks
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> list[ClipTask]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        ClipTask(
            clip_id=item["clip_id"],
            clip_path=Path(item["clip_path"]),
            frame_path=Path(item["frame_path"]),
            width=item["width"],
            height=item["height"],
            expected_resolution=item["expected_resolution"],
            state=item["state"],
        )
        for item in raw
    ]
