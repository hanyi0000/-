from dataclasses import dataclass
from pathlib import Path

from .paths import ProjectPaths, build_project_paths as _build_project_paths
from .runner import build_single_clip_flow_summary as _build_single_clip_flow_summary


@dataclass(frozen=True)
class LiveRunRequest:
    clip_id: str
    state_path: Path
    downloads_dir: Path
    rendered_output_path: Path


def build_project_paths(project_dir: Path) -> ProjectPaths:
    return _build_project_paths(project_dir)


def build_single_clip_flow_summary(project_dir: Path, clip_id: str) -> dict[str, str]:
    return _build_single_clip_flow_summary(project_dir, clip_id)


def build_live_run_request(project_dir: Path, clip_id: str) -> LiveRunRequest:
    paths = _build_project_paths(project_dir)
    return LiveRunRequest(
        clip_id=clip_id,
        state_path=paths.work_dir / "live_state" / f"{clip_id}.json",
        downloads_dir=paths.work_dir / "downloads",
        rendered_output_path=paths.output_rendered_dir / f"{clip_id}.mp4",
    )


__all__ = [
    "LiveRunRequest",
    "ProjectPaths",
    "build_live_run_request",
    "build_project_paths",
    "build_single_clip_flow_summary",
]
