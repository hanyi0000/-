from pathlib import Path

from scripts.browser_video_remix.paths import build_project_paths


def test_build_project_paths_includes_multiperson_work_dirs(tmp_path: Path) -> None:
    paths = build_project_paths(tmp_path)

    assert paths.work_shots_dir == tmp_path / "work" / "shots"
    assert paths.work_keyframes_dir == tmp_path / "work" / "keyframes"
    assert paths.work_workflow_bindings_dir == tmp_path / "work" / "workflow_bindings"
    assert paths.logs_notifications_dir == tmp_path / "logs" / "notifications"
