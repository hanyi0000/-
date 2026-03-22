from pathlib import Path

from scripts.browser_video_remix.validation import validate_rendered_clip


def test_validate_rendered_clip_reports_missing_file(tmp_path: Path) -> None:
    result = validate_rendered_clip(
        clip_id="clip-0001",
        rendered_path=tmp_path / "missing.mp4",
        expected_width=1920,
        expected_height=1080,
    )

    assert result.is_valid is False
    assert result.reason == "missing_file"
