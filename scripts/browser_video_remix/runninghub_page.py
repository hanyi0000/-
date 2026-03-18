from .browser_executor import ClipExecutionRequest, RunningHubSubmitResult
from .live_state import PauseReason


class RunningHubPageAdapter:
    def __init__(self, workflow_url: str) -> None:
        self.workflow_url = workflow_url

    def submit_render_job(
        self,
        page: object,
        request: ClipExecutionRequest,
    ) -> RunningHubSubmitResult:
        if getattr(page, "login_required", False):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return RunningHubSubmitResult(
            status="submitted",
            task_id=getattr(page, "task_id", None),
            pause_reason=None,
        )
