from dataclasses import dataclass


@dataclass(frozen=True)
class ReplacementAuditResult:
    status: str
    finding_type: str
    confidence: float


def plan_retry_action(result: ReplacementAuditResult, attempt: int, max_attempts: int) -> str:
    if attempt >= max_attempts:
        return "pause_and_notify"
    if result.finding_type in {"role_swap", "not_replaced"}:
        return "choose_alternate_keyframe"
    if result.finding_type in {"partial_replace", "background_drift"}:
        return "strengthen_prompt"
    return "resubmit_runninghub"
