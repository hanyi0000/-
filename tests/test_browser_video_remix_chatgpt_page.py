from pathlib import Path

from scripts.browser_video_remix.browser_executor import ChatGptReferenceRequest
from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_state import PauseReason


class FakeLocator:
    def __init__(self, *, count: int = 0, visible: bool = False) -> None:
        self._count = count
        self._visible = visible
        self.input_files: list[str] = []
        self.filled_values: list[str] = []

    def count(self) -> int:
        return self._count

    def is_visible(self) -> bool:
        return self._visible

    def set_input_files(self, value: str) -> None:
        self.input_files.append(value)

    def fill(self, value: str) -> None:
        self.filled_values.append(value)


class StrictModeLocator(FakeLocator):
    def __init__(self) -> None:
        super().__init__(count=2, visible=True)
        self.first = FakeLocator(count=1, visible=True)

    def is_visible(self) -> bool:
        raise RuntimeError("strict mode violation")


class FakeChatGptPage:
    def __init__(
        self,
        *,
        login_button_visible: bool = False,
        login_gate_visible: bool = False,
        has_file_input: bool = True,
        has_prompt_textarea: bool = True,
    ) -> None:
        self.goto_calls: list[tuple[str, str]] = []
        self.locators: dict[str, FakeLocator] = {}
        if has_file_input:
            self.locators["#upload-files"] = FakeLocator(count=1)
        if has_prompt_textarea:
            self.locators["textarea[name='prompt-textarea']"] = FakeLocator(count=1)
        self.role_locators = {
            ("button", "登录"): FakeLocator(
                count=1 if login_button_visible else 0,
                visible=login_button_visible,
            )
        }
        self.text_locators = {
            ChatGptPageAdapter.LOGIN_REQUIRED_TEXT: FakeLocator(
                count=1 if login_gate_visible else 0,
                visible=login_gate_visible,
            )
        }

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())

    def get_by_role(self, role: str, name: str) -> FakeLocator:
        return self.role_locators.get((role, name), FakeLocator())

    def get_by_text(self, text: str) -> FakeLocator:
        return self.text_locators.get(text, FakeLocator())


def test_chatgpt_adapter_pauses_when_login_is_required() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    result = adapter.submit_reference_generation(
        page=FakeChatGptPage(login_button_visible=True),
        request=ChatGptReferenceRequest(
            clip_id="clip-0001",
            frame_path=Path("work/frames/clip-0001.png"),
            output_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
        ),
    )

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.LOGIN_REQUIRED


def test_chatgpt_adapter_ensure_session_handles_multi_match_login_button() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage()
    page.role_locators[("button", adapter.LOGIN_BUTTON_TEXTS[0])] = StrictModeLocator()

    result = adapter.ensure_session(page)

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.LOGIN_REQUIRED


def test_chatgpt_adapter_ensure_session_opens_start_url() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage()

    result = adapter.ensure_session(page)

    assert page.goto_calls == [("https://chatgpt.com/g/test", "domcontentloaded")]
    assert result.status == "ready"
    assert result.pause_reason is None


def test_chatgpt_adapter_submit_reference_generation_uploads_frame_and_prompt() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage()
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=Path("work/frames/clip-0001.png"),
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert page.locators["#upload-files"].input_files == ["work/frames/clip-0001.png"]
    assert page.locators["textarea[name='prompt-textarea']"].filled_values == [
        "replace actor_a with jett"
    ]
    assert result.status == "submitted"
    assert result.output_path == request.output_path


def test_chatgpt_adapter_pauses_when_prompt_textarea_is_missing() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    result = adapter.submit_reference_generation(
        page=FakeChatGptPage(has_prompt_textarea=False),
        request=ChatGptReferenceRequest(
            clip_id="clip-0001",
            frame_path=Path("work/frames/clip-0001.png"),
            output_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
        ),
    )

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.SELECTOR_MISSING


def test_chatgpt_adapter_capture_snapshot_uses_start_url(tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")

    def fake_snapshotter(
        *,
        context: object,
        url: str,
        screenshot_path: Path,
        html_path: Path,
    ) -> None:
        captured["context"] = context
        captured["url"] = url
        captured["screenshot_path"] = screenshot_path
        captured["html_path"] = html_path

    context = object()
    screenshot_path = tmp_path / "logs" / "chatgpt-page.png"
    html_path = tmp_path / "logs" / "chatgpt-page.html"

    adapter.capture_snapshot(
        context=context,
        screenshot_path=screenshot_path,
        html_path=html_path,
        snapshotter=fake_snapshotter,
    )

    assert captured["context"] is context
    assert captured["url"] == "https://chatgpt.com/g/test"
    assert captured["screenshot_path"] == screenshot_path
    assert captured["html_path"] == html_path
