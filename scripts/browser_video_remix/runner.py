from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatchRunPlan:
    project_dir: Path
    clip_count: int
    dry_run: bool


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
