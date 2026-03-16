from pathlib import Path

from .paths import ProjectPaths, build_project_paths as _build_project_paths


def build_project_paths(project_dir: Path) -> ProjectPaths:
    return _build_project_paths(project_dir)


__all__ = ["ProjectPaths", "build_project_paths"]
