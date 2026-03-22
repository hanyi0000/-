from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project_dir: Path
    input_dir: Path
    work_dir: Path
    work_clips_dir: Path
    work_shots_dir: Path
    work_face_detections_dir: Path
    work_keyframes_dir: Path
    work_frames_dir: Path
    work_chatgpt_refs_dir: Path
    work_workflow_bindings_dir: Path
    work_quality_reports_dir: Path
    output_dir: Path
    output_rendered_dir: Path
    output_failed_dir: Path
    logs_dir: Path
    logs_notifications_dir: Path
    runninghub_pauses_dir: Path


def build_project_paths(project_dir: Path) -> ProjectPaths:
    work_dir = project_dir / "work"
    output_dir = project_dir / "output"

    return ProjectPaths(
        project_dir=project_dir,
        input_dir=project_dir / "input",
        work_dir=work_dir,
        work_clips_dir=work_dir / "clips",
        work_shots_dir=work_dir / "shots",
        work_face_detections_dir=work_dir / "face_detections",
        work_keyframes_dir=work_dir / "keyframes",
        work_frames_dir=work_dir / "frames",
        work_chatgpt_refs_dir=work_dir / "chatgpt_refs",
        work_workflow_bindings_dir=work_dir / "workflow_bindings",
        work_quality_reports_dir=work_dir / "quality_reports",
        output_dir=output_dir,
        output_rendered_dir=output_dir / "rendered",
        output_failed_dir=output_dir / "failed",
        logs_dir=project_dir / "logs",
        logs_notifications_dir=project_dir / "logs" / "notifications",
        runninghub_pauses_dir=project_dir / "logs" / "runninghub-pauses",
    )
