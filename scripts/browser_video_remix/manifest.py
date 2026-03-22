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
    start_ms: int
    end_ms: int
    retry_count: int
    person_reference_images: dict[str, str]


def build_clip_task(
    clip_id: str,
    clip_path: Path,
    frame_path: Path,
    width: int,
    height: int,
    start_ms: int = 0,
    end_ms: int = 0,
) -> ClipTask:
    return ClipTask(
        clip_id=clip_id,
        clip_path=clip_path,
        frame_path=frame_path,
        width=width,
        height=height,
        expected_resolution=f"{width}x{height}",
        state="pending",
        start_ms=start_ms,
        end_ms=end_ms,
        retry_count=0,
        person_reference_images={},
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
            "start_ms": task.start_ms,
            "end_ms": task.end_ms,
            "retry_count": task.retry_count,
            "person_reference_images": task.person_reference_images,
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
            start_ms=int(item.get("start_ms", 0)),
            end_ms=int(item.get("end_ms", 0)),
            retry_count=int(item.get("retry_count", 0)),
            person_reference_images={
                str(person_id): str(image_path)
                for person_id, image_path in item.get("person_reference_images", {}).items()
            },
        )
        for item in raw
    ]
