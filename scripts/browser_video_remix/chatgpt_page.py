import base64
import mimetypes
from pathlib import Path

from .browser_executor import AdapterResult, ChatGptReferenceRequest, PersonReferenceRequest
from .live_state import PauseReason
from .playwright_driver import capture_page_snapshot


class ChatGptPageAdapter:
    FILE_INPUT_SELECTORS = ("#upload-files", "#upload-photos")
    PROMPT_INPUT_SELECTORS = (
        "textarea[name='prompt-textarea']",
        "#prompt-textarea[contenteditable='true']",
    )
    RESULT_IMAGE_SELECTORS = (
        "[data-message-author-role='assistant'] img",
        "img[alt*='已生成图片']",
        "img[alt*='Generated image' i]",
    )
    SEND_BUTTON_SELECTOR = "[data-testid='send-button']"
    DRAG_DROP_EVENTS = ("dragenter", "dragover", "drop")
    GENERATED_IMAGE_TIMEOUT_MS = 120_000
    LOGIN_BUTTON_TEXTS = ("\u767b\u5f55", "Log in")
    LOGIN_REQUIRED_TEXT = (
        "\u767b\u5f55\u4ee5\u83b7\u53d6\u57fa\u4e8e\u5df2\u4fdd\u5b58\u804a\u5929\u7684"
        "\u56de\u7b54\uff0c\u5e76\u53ef\u521b\u5efa\u56fe\u7247\u548c\u4e0a\u4f20\u6587\u4ef6\u3002"
    )

    def __init__(self, start_url: str) -> None:
        self.start_url = start_url

    def ensure_session(self, page: object) -> AdapterResult:
        page.goto(self.start_url, wait_until="domcontentloaded")
        if self._is_challenge_page(page):
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.CAPTCHA_REQUIRED,
            )
        if self._is_login_required(page):
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return AdapterResult(
            status="ready",
            output_path=None,
            pause_reason=None,
        )

    def submit_reference_generation(
        self,
        page: object,
        request: ChatGptReferenceRequest | PersonReferenceRequest,
    ) -> AdapterResult:
        session_result = self.ensure_session(page)
        if session_result.pause_reason is not None:
            return session_result

        file_input = self._find_first_available_locator(
            page,
            self.FILE_INPUT_SELECTORS,
            require_visible=False,
        )
        prompt_input = self._find_first_available_locator(
            page,
            self.PROMPT_INPUT_SELECTORS,
            require_visible=True,
        )
        send_button = self._find_required_locator(page, self.SEND_BUTTON_SELECTOR)
        if prompt_input is None or send_button is None:
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )

        prompt_input.fill(request.prompt)
        attachment_ready = False
        if file_input is not None:
            attachment_ready = self._upload_via_file_input(
                page,
                file_input,
                request.frame_path,
            )
        if not attachment_ready:
            attachment_ready = self._is_attachment_ready(page, request.frame_path)
        if not attachment_ready:
            attachment_ready = self._upload_via_drag_drop(
                page,
                prompt_input,
                request.frame_path,
            )
        if not attachment_ready:
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.MANUAL_CONFIRMATION_REQUIRED,
            )
        send_button.click()
        if not self._persist_generated_image(page, request.output_path):
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.MANUAL_CONFIRMATION_REQUIRED,
            )
        return AdapterResult(
            status="submitted",
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

    def _is_login_required(self, page: object) -> bool:
        if getattr(page, "login_required", False):
            return True
        for button_text in self.LOGIN_BUTTON_TEXTS:
            locator = self._get_by_role(page, "button", button_text)
            if locator is not None and self._locator_is_visible(locator):
                return True
        login_gate = self._get_by_text(page, self.LOGIN_REQUIRED_TEXT)
        return login_gate is not None and self._locator_is_visible(login_gate)

    def _is_challenge_page(self, page: object) -> bool:
        current_url = str(getattr(page, "url", ""))
        if "__cf_chl_rt_tk=" in current_url:
            return True
        content_getter = getattr(page, "content", None)
        if not callable(content_getter):
            return False
        html = content_getter()
        if "/cdn-cgi/challenge-platform/" not in html:
            return False
        return not self._has_chatgpt_composer(page)

    def _has_chatgpt_composer(self, page: object) -> bool:
        prompt_input = self._find_first_available_locator(
            page,
            self.PROMPT_INPUT_SELECTORS,
            require_visible=True,
        )
        if prompt_input is not None:
            return True
        send_button = self._find_required_locator(page, self.SEND_BUTTON_SELECTOR)
        if send_button is not None:
            return True
        file_input = self._find_first_available_locator(
            page,
            self.FILE_INPUT_SELECTORS,
            require_visible=False,
        )
        return file_input is not None

    def _is_attachment_ready(self, page: object, frame_path: Path) -> bool:
        filename_match = self._get_by_text(page, frame_path.name)
        if filename_match is not None and self._locator_is_visible(filename_match):
            return True
        attachment_locator = self._find_required_locator(page, "[data-testid*='attachment']")
        return attachment_locator is not None and self._locator_is_visible(attachment_locator)

    def _upload_via_drag_drop(
        self,
        page: object,
        prompt_input: object,
        frame_path: Path,
    ) -> bool:
        evaluator = getattr(page, "evaluate_handle", None)
        dispatch_event = getattr(prompt_input, "dispatch_event", None)
        if not callable(evaluator) or not callable(dispatch_event):
            return False

        try:
            file_bytes = frame_path.read_bytes()
        except OSError:
            return False

        mime_type, _ = mimetypes.guess_type(frame_path.name)
        data_transfer = evaluator(
            """
            (payload) => {
              const binary = atob(payload.base64);
              const bytes = new Uint8Array(binary.length);
              for (let index = 0; index < binary.length; index += 1) {
                bytes[index] = binary.charCodeAt(index);
              }
              const transfer = new DataTransfer();
              transfer.items.add(
                new File([bytes], payload.name, { type: payload.mimeType }),
              );
              return transfer;
            }
            """,
            {
                "base64": base64.b64encode(file_bytes).decode("ascii"),
                "name": frame_path.name,
                "mimeType": mime_type or "application/octet-stream",
            },
        )

        return self._perform_upload_action(
            page,
            lambda: self._dispatch_drag_drop_events(dispatch_event, data_transfer),
        )

    def _upload_via_file_input(
        self,
        page: object,
        file_input: object,
        frame_path: Path,
    ) -> bool:
        setter = getattr(file_input, "set_input_files", None)
        if not callable(setter):
            return False
        return self._perform_upload_action(
            page,
            lambda: setter(frame_path.as_posix()),
        )

    def _perform_upload_action(
        self,
        page: object,
        action: object,
    ) -> bool:
        expect_response = getattr(page, "expect_response", None)
        if not callable(action):
            return False
        if not callable(expect_response):
            action()
            return False

        try:
            with expect_response(
                self._is_create_file_response
            ) as create_file_response:
                with expect_response(
                    self._is_process_upload_response
                ) as process_upload_response:
                    action()
        except Exception:
            return False

        return self._response_is_ok(create_file_response.value) and self._response_is_ok(
            process_upload_response.value
        )

    def _is_create_file_response(self, response: object) -> bool:
        url = str(getattr(response, "url", ""))
        return url.endswith("/backend-api/files")

    def _is_process_upload_response(self, response: object) -> bool:
        return "process_upload_stream" in str(getattr(response, "url", ""))

    def _dispatch_drag_drop_events(self, dispatch_event: object, data_transfer: object) -> None:
        for event_name in self.DRAG_DROP_EVENTS:
            dispatch_event(event_name, {"dataTransfer": data_transfer})

    def _persist_generated_image(self, page: object, output_path: Path) -> bool:
        if not self._wait_for_generated_image(page):
            return False
        image_locator = self._find_first_available_locator(
            page,
            self.RESULT_IMAGE_SELECTORS,
            require_visible=True,
        )
        if image_locator is None:
            return False
        screenshot_target = self._select_locator_instance(image_locator)
        screenshot = getattr(screenshot_target, "screenshot", None)
        if not callable(screenshot):
            return False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            screenshot(path=output_path.as_posix())
        except Exception:
            return False
        return output_path.exists() and output_path.stat().st_size > 0

    def _wait_for_generated_image(self, page: object) -> bool:
        waiter = getattr(page, "wait_for_function", None)
        if not callable(waiter):
            return True
        try:
            waiter(
                """
                (selectors) => {
                  return selectors.some((selector) => {
                    const images = Array.from(document.querySelectorAll(selector));
                    return images.some((image) => {
                      const rect = image.getBoundingClientRect();
                      return (
                        image.complete &&
                        rect.width >= 64 &&
                        rect.height >= 64
                      );
                    });
                  });
                }
                """,
                arg=self.RESULT_IMAGE_SELECTORS,
                timeout=self.GENERATED_IMAGE_TIMEOUT_MS,
            )
        except Exception:
            return False
        return True

    def _find_required_locator(self, page: object, selector: str) -> object | None:
        locator_factory = getattr(page, "locator", None)
        if not callable(locator_factory):
            return None
        locator = locator_factory(selector)
        if self._locator_count(locator) <= 0:
            return None
        return locator

    def _find_first_available_locator(
        self,
        page: object,
        selectors: tuple[str, ...],
        require_visible: bool,
    ) -> object | None:
        for selector in selectors:
            locator = self._find_required_locator(page, selector)
            if locator is None:
                continue
            if self._locator_is_visible(locator):
                return locator
            if not require_visible:
                return locator
        return None

    def _get_by_role(self, page: object, role: str, name: str) -> object | None:
        getter = getattr(page, "get_by_role", None)
        if not callable(getter):
            return None
        return getter(role, name=name)

    def _get_by_text(self, page: object, text: str) -> object | None:
        getter = getattr(page, "get_by_text", None)
        if not callable(getter):
            return None
        return getter(text)

    def _locator_count(self, locator: object) -> int:
        counter = getattr(locator, "count", None)
        if not callable(counter):
            return 0
        return int(counter())

    def _locator_is_visible(self, locator: object) -> bool:
        count = self._locator_count(locator)
        if count <= 0:
            return False
        if count > 1:
            first = getattr(locator, "first", None)
            if first is not None:
                return self._locator_is_visible(first)
            return True
        visible = getattr(locator, "is_visible", None)
        if callable(visible):
            return bool(visible())
        return True

    def _select_locator_instance(self, locator: object) -> object:
        count = self._locator_count(locator)
        if count <= 1:
            return locator
        last = getattr(locator, "last", None)
        if last is not None:
            return last
        first = getattr(locator, "first", None)
        if first is not None:
            return first
        return locator

    def _response_is_ok(self, response: object | None) -> bool:
        if response is None:
            return False
        return bool(getattr(response, "ok", False))
