from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    clip_id: str
    is_valid: bool
    reason: str


def validate_rendered_clip(
    clip_id: str,
    rendered_path: Path,
    expected_width: int,
    expected_height: int,
) -> ValidationResult:
    del expected_width, expected_height

    if not rendered_path.exists():
        return ValidationResult(
            clip_id=clip_id,
            is_valid=False,
            reason="missing_file",
        )

    return ValidationResult(
        clip_id=clip_id,
        is_valid=True,
        reason="ok",
    )
