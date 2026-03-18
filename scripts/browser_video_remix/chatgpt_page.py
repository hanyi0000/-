from pathlib import Path

from .browser_executor import AdapterResult, ChatGptReferenceRequest
from .live_state import PauseReason
from .playwright_driver import capture_page_snapshot


class ChatGptPageAdapter:
    def __init__(self, start_url: str) -> None:
        self.start_url = start_url

    def submit_reference_generation(
        self,
        page: object,
        request: ChatGptReferenceRequest,
    ) -> AdapterResult:
        if getattr(page, "login_required", False):
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return AdapterResult(
            status="completed",
            output_path=request.output_path,
            pause_reason=None,
        )

    def capture_snapshot(
        self,
        context: object,
        screenshot_path: Path,
        html_path: Path,
        snapshotter: object = capture_page_snapshot,
    ) -> None:
        snapshotter(
            context=context,
            url=self.start_url,
            screenshot_path=screenshot_path,
            html_path=html_path,
        )
