from pathlib import Path

from scripts.browser_video_remix.browser_executor import ClipExecutionRequest
from scripts.browser_video_remix.live_state import PauseReason
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


class FakeLocator:
    def __init__(
        self,
        *,
        count: int = 0,
        visible: bool = False,
        text: str = "",
        attributes: dict[str, str] | None = None,
    ) -> None:
        self._count = count
        self._visible = visible
        self._text = text
        self._attributes = attributes or {}
        self.input_files: list[str] = []
        self.filled_values: list[str] = []
        self.clicks = 0

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible

    def set_input_files(self, value: str) -> None:
        self.input_files.append(value)

    def fill(self, value: str) -> None:
        self.filled_values.append(value)

    def click(self) -> None:
        self.clicks += 1

    def inner_text(self) -> str:
        return self._text

    def text_content(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        return self._attributes.get(name)


class FakeRunningHubPage:
    def __init__(
        self,
        *,
        login_required: bool = False,
        task_id: str = "task-123",
        has_video_input: bool = False,
        has_image_input: bool = False,
        has_submit_button: bool = False,
        has_width_input: bool = False,
        has_height_input: bool = False,
    ) -> None:
        self.login_required = login_required
        self.task_id = task_id
        self.goto_calls: list[tuple[str, str]] = []
        self.locators: dict[str, FakeLocator] = {}
        if has_video_input:
            self.locators["#video-upload"] = FakeLocator(count=1)
        if has_image_input:
            self.locators["#image-upload"] = FakeLocator(count=1)
        if has_width_input:
            self.locators["input[name='width']"] = FakeLocator(count=1, visible=True)
        if has_height_input:
            self.locators["input[name='height']"] = FakeLocator(count=1, visible=True)
        if has_submit_button:
            self.locators["button[data-testid='submit-workflow']"] = FakeLocator(
                count=1,
                visible=True,
            )
        self.locators["[data-testid='task-id']"] = FakeLocator(
            count=1,
            visible=True,
            text=task_id,
        )

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())


def test_runninghub_adapter_pauses_when_login_is_required() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(login_required=True)

    result = adapter.submit_render_job(
        page=page,
        request=ClipExecutionRequest(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
            width=1920,
            height=1080,
        ),
    )

    assert page.goto_calls == [("https://example.com/workflow", "domcontentloaded")]
    assert result.status == "paused"
    assert result.pause_reason == PauseReason.LOGIN_REQUIRED


def test_runninghub_adapter_uploads_video_and_reference_and_reads_task_id() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(
        task_id="task-123",
        has_video_input=True,
        has_image_input=True,
        has_submit_button=True,
        has_width_input=True,
        has_height_input=True,
    )

    result = adapter.submit_render_job(
        page=page,
        request=ClipExecutionRequest(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
            width=1920,
            height=1080,
        ),
    )

    assert page.goto_calls == [("https://example.com/workflow", "domcontentloaded")]
    assert page.locators["#video-upload"].input_files == ["work/clips/clip-0001.mp4"]
    assert page.locators["#image-upload"].input_files == ["work/chatgpt_refs/clip-0001.png"]
    assert page.locators["input[name='width']"].filled_values[-1] == "1920"
    assert page.locators["input[name='height']"].filled_values[-1] == "1080"
    assert page.locators["button[data-testid='submit-workflow']"].clicks == 1
    assert result.status == "submitted"
    assert result.task_id == "task-123"
