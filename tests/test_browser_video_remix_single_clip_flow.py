from pathlib import Path

from scripts.browser_video_remix.runner import build_single_clip_flow_summary


def test_build_single_clip_flow_summary_includes_manifest_and_render_target(
    tmp_path: Path,
) -> None:
    summary = build_single_clip_flow_summary(
        project_dir=tmp_path / "projects" / "demo",
        clip_id="clip-0001",
    )

    assert summary["clip_id"] == "clip-0001"
    assert summary["manifest_path"].endswith("manifest.json")
    assert summary["render_output"].endswith("clip-0001.mp4")
