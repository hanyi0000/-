from pathlib import Path

from .paths import ProjectPaths, build_project_paths as _build_project_paths
from .runner import build_single_clip_flow_summary as _build_single_clip_flow_summary


def build_project_paths(project_dir: Path) -> ProjectPaths:
    return _build_project_paths(project_dir)


def build_single_clip_flow_summary(project_dir: Path, clip_id: str) -> dict[str, str]:
    return _build_single_clip_flow_summary(project_dir, clip_id)


__all__ = ["ProjectPaths", "build_project_paths", "build_single_clip_flow_summary"]
