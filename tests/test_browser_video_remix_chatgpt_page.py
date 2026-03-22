from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
    ChatGptReferenceRequest,
    PersonReferenceRequest,
)
from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_state import PauseReason


class FakeLocator:
    def __init__(
        self,
        *,
        count: int = 0,
        visible: bool = False,
        screenshot_bytes: bytes | None = None,
    ) -> None:
        self._count = count
        self._visible = visible
        self.input_files: list[str] = []
        self.filled_values: list[str] = []
        self.clicks = 0
        self.dispatch_events: list[tuple[str, object | None]] = []
        self.screenshot_bytes = screenshot_bytes
        self.screenshot_paths: list[str] = []

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

    def dispatch_event(self, event_name: str, event_init: object | None = None) -> None:
        self.dispatch_events.append((event_name, event_init))

    def screenshot(self, path: str) -> None:
        self.screenshot_paths.append(path)
        if self.screenshot_bytes is None:
            raise RuntimeError("screenshot bytes not configured")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.screenshot_bytes)


class StrictModeLocator(FakeLocator):
    def __init__(self) -> None:
        super().__init__(count=2, visible=True)
        self.first = FakeLocator(count=1, visible=True)

    def is_visible(self) -> bool:
        raise RuntimeError("strict mode violation")


class FakeResponse:
    def __init__(self, url: str, *, ok: bool = True) -> None:
        self.url = url
        self.ok = ok


class FakeExpectResponse:
    def __init__(self, response: FakeResponse | None) -> None:
        self.value = response

    def __enter__(self) -> "FakeExpectResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class FakeChatGptPage:
    def __init__(
        self,
        *,
        login_button_visible: bool = False,
        login_gate_visible: bool = False,
        has_file_input: bool = True,
        has_prompt_textarea: bool = True,
        has_upload_photos_input: bool = True,
        upload_files_visible: bool = False,
        upload_photos_visible: bool = False,
        has_contenteditable_prompt: bool = False,
        attachment_visible: bool = False,
        file_input_upload_success: bool = False,
        drop_upload_success: bool = False,
        has_generated_image: bool = False,
        has_generated_viewer_image: bool = False,
        generated_image_bytes: bytes = b"generated-image-bytes",
        url: str = "https://chatgpt.com/g/test",
        html: str = "",
    ) -> None:
        self.goto_calls: list[tuple[str, str]] = []
        self.url = url
        self.html = html
        self.attachment_visible = attachment_visible
        self.has_generated_image = has_generated_image
        self.has_generated_viewer_image = has_generated_viewer_image
        self.evaluate_handle_calls: list[object] = []
        self.expect_response_calls = 0
        self.wait_for_function_calls: list[tuple[str, object | None, object | None]] = []
        self.locators: dict[str, FakeLocator] = {}
        self.expected_responses: list[FakeResponse] = []
        if file_input_upload_success:
            self.expected_responses.extend(
                [
                    FakeResponse("https://chatgpt.com/backend-api/files"),
                    FakeResponse("https://chatgpt.com/backend-api/files/process_upload_stream"),
                ]
            )
        if drop_upload_success:
            self.expected_responses.extend(
                [
                    FakeResponse("https://chatgpt.com/backend-api/files"),
                    FakeResponse("https://chatgpt.com/backend-api/files/process_upload_stream"),
                ]
            )
        if has_file_input:
            self.locators["#upload-files"] = FakeLocator(count=1, visible=upload_files_visible)
        if has_upload_photos_input:
            self.locators["#upload-photos"] = FakeLocator(count=1, visible=upload_photos_visible)
        if has_prompt_textarea:
            self.locators["textarea[name='prompt-textarea']"] = FakeLocator(
                count=1,
                visible=True,
            )
        if has_contenteditable_prompt:
            self.locators["#prompt-textarea[contenteditable='true']"] = FakeLocator(
                count=1,
                visible=True,
            )
        if has_generated_image:
            self.locators["[data-message-author-role='assistant'] img"] = FakeLocator(
                count=1,
                visible=True,
                screenshot_bytes=generated_image_bytes,
            )
        if has_generated_viewer_image:
            self.locators["img[alt*='Generated image' i]"] = FakeLocator(
                count=1,
                visible=True,
                screenshot_bytes=generated_image_bytes,
            )
        self.locators["[data-testid='send-button']"] = FakeLocator(count=1, visible=True)
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
            ),
            "chatgpt-edge-proxy-smoke.png": FakeLocator(
                count=1 if attachment_visible else 0,
                visible=attachment_visible,
            ),
        }

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))
        self.url = url

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())

    def get_by_role(self, role: str, name: str) -> FakeLocator:
        return self.role_locators.get((role, name), FakeLocator())

    def get_by_text(self, text: str) -> FakeLocator:
        if self.attachment_visible and text.endswith(".png"):
            return FakeLocator(count=1, visible=True)
        return self.text_locators.get(text, FakeLocator())

    def content(self) -> str:
        return self.html

    def evaluate_handle(self, script: str, payload: object) -> dict[str, object]:
        self.evaluate_handle_calls.append((script, payload))
        return {"payload": payload}

    def expect_response(self, predicate: object) -> FakeExpectResponse:
        self.expect_response_calls += 1
        response = self.expected_responses.pop(0) if self.expected_responses else None
        return FakeExpectResponse(response)

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: object | None = None,
        timeout: object | None = None,
    ) -> None:
        self.wait_for_function_calls.append((expression, arg, timeout))
        if not self.has_generated_image and not self.has_generated_viewer_image:
            raise TimeoutError("generated image not ready")


class TimeoutChatGptPage(FakeChatGptPage):
    def goto(self, url: str, wait_until: str) -> None:
        super().goto(url, wait_until)
        raise TimeoutError("navigation timed out")


class ProxyFailureChatGptPage(FakeChatGptPage):
    def goto(self, url: str, wait_until: str) -> None:
        super().goto(url, wait_until)
        raise RuntimeError("Page.goto: net::ERR_PROXY_CONNECTION_FAILED at https://chatgpt.com/")


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


def test_chatgpt_adapter_pauses_when_initial_navigation_times_out() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = TimeoutChatGptPage()

    result = adapter.ensure_session(page)

    assert page.goto_calls == [("https://chatgpt.com/g/test", "domcontentloaded")]
    assert result.status == "paused"
    assert result.pause_reason == PauseReason.MANUAL_CONFIRMATION_REQUIRED


def test_chatgpt_adapter_reports_proxy_connection_failures_precisely() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = ProxyFailureChatGptPage()

    result = adapter.ensure_session(page)

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.PROXY_CONNECTION_FAILED


def test_chatgpt_adapter_pauses_when_cloudflare_challenge_is_present() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/?__cf_chl_rt_tk=example")
    page = FakeChatGptPage(
        html='<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script>',
    )

    result = adapter.ensure_session(page)

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.CAPTCHA_REQUIRED


def test_chatgpt_adapter_does_not_treat_normal_shell_as_challenge() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage(
        html='<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1"></script>',
    )

    result = adapter.ensure_session(page)

    assert result.status == "ready"
    assert result.pause_reason is None


def test_chatgpt_adapter_submit_reference_generation_uploads_frame_and_prompt() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage(attachment_visible=True, has_generated_image=True)
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
    assert page.locators["[data-testid='send-button']"].clicks == 1
    assert result.status == "submitted"
    assert result.output_path == request.output_path


def test_chatgpt_adapter_uses_contenteditable_prompt_when_textarea_is_missing() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    result = adapter.submit_reference_generation(
        page=FakeChatGptPage(
            has_prompt_textarea=False,
            has_contenteditable_prompt=True,
            attachment_visible=True,
            has_generated_image=True,
        ),
        request=ChatGptReferenceRequest(
            clip_id="clip-0001",
            frame_path=Path("work/frames/clip-0001.png"),
            output_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
        ),
    )

    assert result.status == "submitted"
    assert result.pause_reason is None


def test_chatgpt_adapter_pauses_when_attachment_is_not_confirmed() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage(attachment_visible=False)
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=Path("work/frames/chatgpt-edge-proxy-smoke.png"),
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert page.locators["[data-testid='send-button']"].clicks == 0
    assert result.status == "paused"
    assert result.pause_reason == PauseReason.MANUAL_CONFIRMATION_REQUIRED


def test_chatgpt_adapter_submits_when_drag_drop_upload_completes(tmp_path: Path) -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage(
        has_file_input=False,
        has_upload_photos_input=False,
        has_prompt_textarea=False,
        has_contenteditable_prompt=True,
        attachment_visible=False,
        drop_upload_success=True,
        has_generated_image=True,
    )
    frame_path = tmp_path / "chatgpt-edge-proxy-smoke.png"
    frame_path.write_bytes(b"fake-png")
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=frame_path,
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert [
        event_name
        for event_name, _ in page.locators["#prompt-textarea[contenteditable='true']"].dispatch_events
    ] == ["dragenter", "dragover", "drop"]
    assert page.expect_response_calls == 2
    assert page.locators["[data-testid='send-button']"].clicks == 1
    assert result.status == "submitted"


def test_chatgpt_adapter_submits_when_file_input_upload_completes() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage(
        attachment_visible=False,
        file_input_upload_success=True,
        has_generated_image=True,
    )
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=Path("work/frames/chatgpt-edge-proxy-smoke.png"),
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert page.expect_response_calls == 2
    assert page.locators["textarea[name='prompt-textarea']"].dispatch_events == []
    assert page.locators["[data-testid='send-button']"].clicks == 1
    assert result.status == "submitted"


def test_chatgpt_adapter_prefers_visible_upload_input_before_hidden_upload_files() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    page = FakeChatGptPage(
        attachment_visible=False,
        has_generated_image=True,
        upload_files_visible=False,
        upload_photos_visible=True,
    )
    attempted_inputs: list[object] = []

    def fake_upload(current_page: object, file_input: object, frame_path: Path) -> bool:
        del current_page, frame_path
        attempted_inputs.append(file_input)
        return file_input is page.locators["#upload-photos"]

    adapter._upload_via_file_input = fake_upload  # type: ignore[method-assign]
    adapter._upload_via_drag_drop = lambda *args: False  # type: ignore[method-assign]
    adapter._is_attachment_ready = lambda *args: False  # type: ignore[method-assign]

    result = adapter.submit_reference_generation(
        page=page,
        request=ChatGptReferenceRequest(
            clip_id="clip-0001",
            frame_path=Path("work/frames/clip-0001.png"),
            output_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
        ),
    )

    assert attempted_inputs == [page.locators["#upload-photos"]]
    assert page.locators["[data-testid='send-button']"].clicks == 1
    assert result.status == "submitted"


def test_chatgpt_adapter_create_file_matcher_excludes_process_upload_stream() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")

    assert adapter._is_create_file_response(
        FakeResponse("https://chatgpt.com/backend-api/files")
    ) is True
    assert adapter._is_create_file_response(
        FakeResponse("https://chatgpt.com/backend-api/files/process_upload_stream")
    ) is False
    assert adapter._is_process_upload_response(
        FakeResponse("https://chatgpt.com/backend-api/files/process_upload_stream")
    ) is True


def test_chatgpt_adapter_saves_generated_reference_image_to_output_path(
    tmp_path: Path,
) -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    output_path = tmp_path / "work" / "chatgpt_refs" / "clip-0001.png"
    page = FakeChatGptPage(
        attachment_visible=True,
        has_generated_image=True,
        generated_image_bytes=b"generated-reference-image",
    )
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=Path("work/frames/chatgpt-edge-proxy-smoke.png"),
        output_path=output_path,
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert len(page.wait_for_function_calls) == 1
    assert (
        page.locators["[data-message-author-role='assistant'] img"].screenshot_paths
        == [output_path.as_posix()]
    )
    assert output_path.read_bytes() == b"generated-reference-image"
    assert result.status == "submitted"
    assert result.output_path == output_path


def test_chatgpt_adapter_saves_generated_reference_image_for_one_person_request(
    tmp_path: Path,
) -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    output_path = tmp_path / "work" / "chatgpt_refs" / "clip-0001_actor_a.png"
    page = FakeChatGptPage(
        attachment_visible=True,
        has_generated_image=True,
        generated_image_bytes=b"generated-reference-image",
    )
    request = PersonReferenceRequest(
        clip_id="clip-0001",
        source_person_id="actor_a",
        frame_path=Path("work/keyframes/clip-0001_actor_a.png"),
        output_path=output_path,
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert output_path.read_bytes() == b"generated-reference-image"
    assert result.status == "submitted"
    assert result.output_path == output_path


def test_chatgpt_adapter_saves_generated_image_from_dedicated_viewer_ui(
    tmp_path: Path,
) -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    output_path = tmp_path / "work" / "chatgpt_refs" / "clip-0001.png"
    page = FakeChatGptPage(
        attachment_visible=True,
        has_generated_viewer_image=True,
        generated_image_bytes=b"generated-reference-image",
    )
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=Path("work/frames/chatgpt-edge-proxy-smoke.png"),
        output_path=output_path,
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert len(page.wait_for_function_calls) == 1
    assert page.locators["img[alt*='Generated image' i]"].screenshot_paths == [
        output_path.as_posix()
    ]
    assert output_path.read_bytes() == b"generated-reference-image"
    assert result.status == "submitted"
    assert result.output_path == output_path


def test_chatgpt_adapter_pauses_when_generated_reference_image_never_appears(
    tmp_path: Path,
) -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    output_path = tmp_path / "work" / "chatgpt_refs" / "clip-0001.png"
    page = FakeChatGptPage(attachment_visible=True)
    request = ChatGptReferenceRequest(
        clip_id="clip-0001",
        frame_path=Path("work/frames/chatgpt-edge-proxy-smoke.png"),
        output_path=output_path,
        prompt="replace actor_a with jett",
    )

    result = adapter.submit_reference_generation(page=page, request=request)

    assert len(page.wait_for_function_calls) == 1
    assert page.locators["[data-testid='send-button']"].clicks == 1
    assert output_path.exists() is False
    assert result.status == "paused"
    assert result.pause_reason == PauseReason.MANUAL_CONFIRMATION_REQUIRED


def test_chatgpt_adapter_pauses_when_all_prompt_inputs_are_missing() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    result = adapter.submit_reference_generation(
        page=FakeChatGptPage(
            has_prompt_textarea=False,
            has_contenteditable_prompt=False,
        ),
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
