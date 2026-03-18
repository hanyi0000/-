from .browser_executor import ClipExecutionRequest, RunningHubSubmitResult
from .live_state import PauseReason


class RunningHubPageAdapter:
    VIDEO_INPUT_SELECTORS = ("#video-upload", "input[type='file'][accept*='video']")
    IMAGE_INPUT_SELECTORS = ("#image-upload", "input[type='file'][accept*='image']")
    WIDTH_INPUT_SELECTORS = ("input[name='width']", "#width")
    HEIGHT_INPUT_SELECTORS = ("input[name='height']", "#height")
    SUBMIT_BUTTON_SELECTORS = ("button[data-testid='submit-workflow']", "button")
    TASK_ID_SELECTORS = ("[data-testid='task-id']", "[data-task-id]")

    def __init__(self, workflow_url: str) -> None:
        self.workflow_url = workflow_url

    def ensure_session(self, page: object) -> RunningHubSubmitResult:
        page.goto(self.workflow_url, wait_until="domcontentloaded")
        if getattr(page, "login_required", False):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return RunningHubSubmitResult(
            status="ready",
            task_id=None,
            pause_reason=None,
        )

    def submit_render_job(
        self,
        page: object,
        request: ClipExecutionRequest,
    ) -> RunningHubSubmitResult:
        session_result = self.ensure_session(page)
        if session_result.pause_reason is not None:
            return session_result

        video_input = self._find_first_available_locator(
            page,
            self.VIDEO_INPUT_SELECTORS,
            require_visible=False,
        )
        image_input = self._find_first_available_locator(
            page,
            self.IMAGE_INPUT_SELECTORS,
            require_visible=False,
        )
        width_input = self._find_first_available_locator(
            page,
            self.WIDTH_INPUT_SELECTORS,
            require_visible=True,
        )
        height_input = self._find_first_available_locator(
            page,
            self.HEIGHT_INPUT_SELECTORS,
            require_visible=True,
        )
        submit_button = self._find_first_available_locator(
            page,
            self.SUBMIT_BUTTON_SELECTORS,
            require_visible=True,
        )
        if None in {video_input, image_input, width_input, height_input, submit_button}:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.SELECTOR_MISSING,
            )

        video_input.set_input_files(request.clip_path.as_posix())
        image_input.set_input_files(request.reference_image_path.as_posix())
        width_input.fill(str(request.width))
        height_input.fill(str(request.height))
        submit_button.click()

        task_id = self._extract_task_id(page)
        if not task_id:
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.MANUAL_CONFIRMATION_REQUIRED,
            )
        return RunningHubSubmitResult(
            status="submitted",
            task_id=task_id,
            pause_reason=None,
        )

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
        *,
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

    def _extract_task_id(self, page: object) -> str | None:
        for selector in self.TASK_ID_SELECTORS:
            locator = self._find_required_locator(page, selector)
            if locator is None:
                continue
            for reader_name in ("inner_text", "text_content"):
                reader = getattr(locator, reader_name, None)
                if callable(reader):
                    value = str(reader()).strip()
                    if value:
                        return value
            attribute_reader = getattr(locator, "get_attribute", None)
            if callable(attribute_reader):
                value = attribute_reader("data-task-id")
                if value:
                    return str(value).strip()
        task_id = getattr(page, "task_id", None)
        if task_id is None:
            return None
        return str(task_id).strip() or None

    def _locator_count(self, locator: object) -> int:
        counter = getattr(locator, "count", None)
        if not callable(counter):
            return 0
        return int(counter())

    def _locator_is_visible(self, locator: object) -> bool:
        count = self._locator_count(locator)
        if count <= 0:
            return False
        visible = getattr(locator, "is_visible", None)
        if callable(visible):
            return bool(visible())
        return True
