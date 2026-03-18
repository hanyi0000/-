from pathlib import Path

from .browser_executor import AdapterResult, ChatGptReferenceRequest
from .live_state import PauseReason
from .playwright_driver import capture_page_snapshot


class ChatGptPageAdapter:
    FILE_INPUT_SELECTORS = ("#upload-photos", "#upload-files")
    PROMPT_INPUT_SELECTORS = (
        "textarea[name='prompt-textarea']",
        "#prompt-textarea[contenteditable='true']",
    )
    SEND_BUTTON_SELECTOR = "[data-testid='send-button']"
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
        request: ChatGptReferenceRequest,
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
        if file_input is None or prompt_input is None or send_button is None:
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )

        file_input.set_input_files(request.frame_path.as_posix())
        prompt_input.fill(request.prompt)
        send_button.click()
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
        return "/cdn-cgi/challenge-platform/" in html

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
