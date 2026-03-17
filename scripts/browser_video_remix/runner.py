from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatchRunPlan:
    project_dir: Path
    clip_count: int
    dry_run: bool


@dataclass(frozen=True)
class PrepareRunPlan:
    project_dir: Path
    clip_count: int
    clips_dir: Path
    frames_dir: Path
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
    work_dir = project_dir / "work"
    return PrepareRunPlan(
        project_dir=project_dir,
        clip_count=clip_count,
        clips_dir=work_dir / "clips",
        frames_dir=work_dir / "frames",
        manifest_path=work_dir / "manifest.json",
    )
