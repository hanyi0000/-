from scripts.browser_video_remix.replacement_audit import (
    ReplacementAuditResult,
    plan_retry_action,
)


def test_plan_retry_for_role_swap_requests_different_best_frame() -> None:
    result = ReplacementAuditResult(
        status="retry",
        finding_type="role_swap",
        confidence=0.91,
    )

    action = plan_retry_action(result, attempt=1, max_attempts=3)

    assert action == "choose_alternate_keyframe"


def test_plan_retry_returns_pause_after_third_failure() -> None:
    result = ReplacementAuditResult(status="retry", finding_type="background_drift", confidence=0.88)

    action = plan_retry_action(result, attempt=3, max_attempts=3)

    assert action == "pause_and_notify"
