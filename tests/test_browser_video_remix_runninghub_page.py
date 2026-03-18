from pathlib import Path

from scripts.browser_video_remix.browser_executor import ClipExecutionRequest
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


class FakeRunningHubPage:
    def __init__(self, login_required: bool = False, task_id: str = "task-123") -> None:
        self.login_required = login_required
        self.task_id = task_id


def test_runninghub_adapter_returns_task_id_for_submitted_job() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    result = adapter.submit_render_job(
        page=FakeRunningHubPage(),
        request=ClipExecutionRequest(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
            width=1920,
            height=1080,
        ),
    )

    assert result.status == "submitted"
    assert result.task_id == "task-123"
    assert result.pause_reason is None
