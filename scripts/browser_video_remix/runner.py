from dataclasses import dataclass
from pathlib import Path

from .paths import build_project_paths


@dataclass(frozen=True)
class BatchRunPlan:
    project_dir: Path
    clip_count: int
    dry_run: bool


@dataclass(frozen=True)
class PrepareRunPlan:
    project_dir: Path
    clip_count: int
    shots_dir: Path
    keyframes_dir: Path
    manifest_path: Path


def plan_batch_run(
    project_dir: Path,
    manifest_entries: list[str],
    dry_run: bool,
) -> BatchRunPlan:
    return BatchRunPlan(
        project_dir=project_dir,
        clip_count=len(manifest_entries),
        dry_run=dry_run,
    )


def plan_prepare_run(project_dir: Path, clip_count: int) -> PrepareRunPlan:
    paths = build_project_paths(project_dir)
    return PrepareRunPlan(
        project_dir=project_dir,
        clip_count=clip_count,
        shots_dir=paths.work_shots_dir,
        keyframes_dir=paths.work_keyframes_dir,
        manifest_path=paths.work_dir / "manifest.json",
    )


def build_single_clip_flow_summary(project_dir: Path, clip_id: str) -> dict[str, str]:
    return {
        "clip_id": clip_id,
        "manifest_path": str(project_dir / "work" / "manifest.json"),
        "render_output": str(project_dir / "output" / "rendered" / f"{clip_id}.mp4"),
    }
