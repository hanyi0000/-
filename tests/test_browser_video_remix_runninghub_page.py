import json
from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
    ClipExecutionRequest,
    RunningHubTaskStatus,
)
from scripts.browser_video_remix.live_state import PauseReason
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter
from scripts.browser_video_remix.workflow_binding import WorkflowBinding, save_workflow_binding


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


class StrictModeLocator(FakeLocator):
    def __init__(self) -> None:
        super().__init__(count=2, visible=True)
        self.first = FakeLocator(count=1, visible=True)

    def is_visible(self) -> bool:
        raise RuntimeError("strict mode violation")


class FakeDownload:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path

    def save_as(self, target_path: str) -> None:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.source_path.read_bytes())


class FakeExpectDownload:
    def __init__(self, download: FakeDownload) -> None:
        self.value = download

    def __enter__(self) -> "FakeExpectDownload":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class FakeRunningHubPage:
    def __init__(
        self,
        *,
        login_required: bool = False,
        task_id: str = "task-123",
        task_status: str = "pending",
        has_video_input: bool = False,
        has_image_input: bool = False,
        has_submit_button: bool = False,
        has_width_input: bool = False,
        has_height_input: bool = False,
        has_download_button: bool = True,
        login_button_visible: bool = False,
        has_generic_submit_button: bool = False,
        strict_generic_submit_button: bool = False,
        downloadable_path: Path | None = None,
        graph_api_available: bool = False,
        graph_task_id: str | None = None,
        graph_workflow_content: dict[str, object] | None = None,
        graph_fetch_results: list[dict[str, object] | None] | None = None,
        graph_cached_workflow_content: dict[str, object] | None = None,
        graph_cached_workflow_results: list[dict[str, object] | None] | None = None,
        graph_loader_ready_results: list[bool] | None = None,
        task_list_records: list[dict[str, object]] | None = None,
        task_list_results: list[list[dict[str, object]]] | None = None,
        task_media_urls: dict[str, str] | None = None,
        task_media_results: list[str | None] | None = None,
        output_history_records: list[dict[str, object]] | None = None,
    ) -> None:
        self.login_required = login_required
        self.task_id = task_id
        self.task_status = task_status
        self.downloadable_path = downloadable_path
        self.goto_calls: list[tuple[str, str]] = []
        self.locators: dict[str, FakeLocator] = {}
        self.graph_api_available = graph_api_available
        self.graph_task_id = graph_task_id
        self.graph_workflow_content = graph_workflow_content or {"nodes": []}
        self.graph_fetch_results = list(graph_fetch_results or [])
        self.graph_cached_workflow_content = graph_cached_workflow_content
        self.graph_cached_workflow_results = list(graph_cached_workflow_results or [])
        self.graph_loader_ready_results = list(graph_loader_ready_results or [])
        self.graph_fetch_calls: list[tuple[str, str]] = []
        self.graph_loaded_workflows: list[dict[str, object]] = []
        self.graph_uploads: list[tuple[int, str]] = []
        self.graph_queue_calls: list[int] = []
        self.wait_for_timeout_calls: list[int] = []
        self.graph_loader_ready_checks = 0
        self.task_list_records = list(task_list_records or [])
        self.task_list_results = list(task_list_results or [])
        self.task_media_urls = dict(task_media_urls or {})
        self.task_media_results = list(task_media_results or [])
        self.output_history_records = list(output_history_records or [])
        self.fetch_runninghub_task_list_calls = 0
        self.fetch_runninghub_output_history_calls = 0
        self.read_task_media_url_calls: list[str] = []
        self.download_url_calls: list[tuple[str, str]] = []
        self.role_locators = {
            ("button", "登录"): FakeLocator(
                count=1 if login_button_visible else 0,
                visible=login_button_visible,
            ),
            ("button", "登 录"): FakeLocator(
                count=1 if login_button_visible else 0,
                visible=login_button_visible,
            ),
            ("button", "Log in"): FakeLocator(
                count=1 if login_button_visible else 0,
                visible=login_button_visible,
            ),
        }
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
        if strict_generic_submit_button:
            self.locators["button"] = StrictModeLocator()
        elif has_generic_submit_button:
            self.locators["button"] = FakeLocator(count=1, visible=True)
        if has_download_button:
            self.locators["button[data-testid='download-render']"] = FakeLocator(
                count=1,
                visible=True,
            )
        self.locators["[data-testid='task-id']"] = FakeLocator(
            count=1,
            visible=True,
            text=task_id,
        )
        self.locators["[data-testid='task-status']"] = FakeLocator(
            count=1,
            visible=True,
            text=task_status,
        )

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())

    def get_by_role(self, role: str, name: str) -> FakeLocator:
        return self.role_locators.get((role, name), FakeLocator())

    def expect_download(self) -> FakeExpectDownload:
        if self.downloadable_path is None:
            raise RuntimeError("downloadable path not configured")
        return FakeExpectDownload(FakeDownload(self.downloadable_path))

    def fetch_workflow_content(self, workflow_id: str, content_type: str) -> dict[str, object] | None:
        self.graph_fetch_calls.append((workflow_id, content_type))
        if self.graph_fetch_results:
            return self.graph_fetch_results.pop(0)
        if not self.graph_api_available:
            return None
        return self.graph_workflow_content

    def load_graph_data(self, workflow: dict[str, object]) -> None:
        self.graph_loaded_workflows.append(workflow)

    def upload_graph_asset(self, node_id: int, file_path: str) -> str:
        self.graph_uploads.append((node_id, file_path))
        return Path(file_path).name

    def queue_graph_prompt(self, number: int) -> str | None:
        self.graph_queue_calls.append(number)
        return self.graph_task_id

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_for_timeout_calls.append(timeout_ms)

    def read_cached_workflow_content(self, workflow_id: str) -> dict[str, object] | None:
        del workflow_id
        if self.graph_cached_workflow_results:
            return self.graph_cached_workflow_results.pop(0)
        return self.graph_cached_workflow_content

    def is_graph_loader_ready(self) -> bool:
        self.graph_loader_ready_checks += 1
        if self.graph_loader_ready_results:
            return self.graph_loader_ready_results.pop(0)
        return True

    def fetch_runninghub_task_list(self) -> list[dict[str, object]]:
        self.fetch_runninghub_task_list_calls += 1
        if self.task_list_results:
            return list(self.task_list_results.pop(0))
        return list(self.task_list_records)

    def read_task_media_url(self, task_id: str) -> str | None:
        self.read_task_media_url_calls.append(task_id)
        if self.task_media_results:
            return self.task_media_results.pop(0)
        return self.task_media_urls.get(task_id)

    def download_url_to_path(self, media_url: str, output_path: str) -> None:
        self.download_url_calls.append((media_url, output_path))
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"downloaded:{media_url}".encode("utf-8"))

    def fetch_runninghub_output_history(self) -> list[dict[str, object]]:
        self.fetch_runninghub_output_history_calls += 1
        return list(self.output_history_records)


class FakeGraphFileInput:
    def __init__(self) -> None:
        self.input_files: list[str] = []

    def set_input_files(self, value: str) -> None:
        self.input_files.append(value)


class StrictWaitGraphFrame:
    def __init__(self) -> None:
        self.url = "https://www.runninghub.cn/comfyUI.html"
        self.file_input = FakeGraphFileInput()
        self.api_file_input = FakeGraphFileInput()
        self.wait_calls: list[tuple[dict[str, object], int]] = []

    def evaluate(self, expression: str, arg: object | None = None) -> bool:
        del expression, arg
        return True

    def locator(self, selector: str) -> FakeGraphFileInput:
        assert selector in {"#comfy-file-input", "#codex-upload-input"}
        if selector == "#codex-upload-input":
            return self.api_file_input
        return self.file_input

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: dict[str, object],
        timeout: int,
    ) -> None:
        del expression
        self.wait_calls.append((arg, timeout))


class ValueChangeGraphFrame(StrictWaitGraphFrame):
    def __init__(self) -> None:
        super().__init__()
        self.evaluate_call_count = 0

    def evaluate(self, expression: str, arg: object | None = None) -> object:
        self.evaluate_call_count += 1
        if self.evaluate_call_count == 1:
            return True
        return ["existing-server-file.mp4"]

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: dict[str, object],
        timeout: int,
    ) -> None:
        del expression
        self.wait_calls.append((arg, timeout))


class DelayedUploadWidgetGraphFrame(StrictWaitGraphFrame):
    def __init__(self, ready_on_attempt: int) -> None:
        super().__init__()
        self.ready_on_attempt = ready_on_attempt
        self.upload_ready_checks = 0

    def evaluate(self, expression: str, arg: object | None = None) -> object:
        del arg
        if "uploadWidget.callback" in expression:
            self.upload_ready_checks += 1
            return self.upload_ready_checks >= self.ready_on_attempt
        if "const collected = []" in expression:
            return ["existing-server-file.mp4"]
        return True


class TimeoutLoadGraphFrame(StrictWaitGraphFrame):
    def wait_for_function(
        self,
        expression: str,
        *,
        arg: dict[str, object],
        timeout: int,
    ) -> None:
        del expression, arg, timeout
        raise TimeoutError("timed out")


class FakeGraphPage:
    def __init__(self, frame: StrictWaitGraphFrame) -> None:
        self._frames = [frame]
        self.wait_for_timeout_calls: list[int] = []

    def frames(self) -> list[StrictWaitGraphFrame]:
        return self._frames

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_for_timeout_calls.append(timeout_ms)


class ErrorGraphFrame(StrictWaitGraphFrame):
    def evaluate(self, expression: str, arg: object | None = None) -> object:
        del expression, arg
        raise RuntimeError("frame failure")


class TimeoutGraphFrame(StrictWaitGraphFrame):
    def evaluate(self, expression: str, arg: object | None = None) -> object:
        if "uploadWidget.callback" in expression:
            return True
        return []

    def wait_for_function(
        self,
        expression: str,
        *,
        arg: dict[str, object],
        timeout: int,
    ) -> None:
        del expression, arg, timeout
        raise TimeoutError("timed out")


class ApiFallbackGraphFrame(TimeoutGraphFrame):
    def __init__(self) -> None:
        super().__init__()
        self.api_upload_args: list[dict[str, object]] = []

    def evaluate(self, expression: str, arg: object | None = None) -> object:
        if "api.fetchApi('/upload/image'" in expression:
            assert isinstance(arg, dict)
            self.api_upload_args.append(arg)
            return "uploaded-server-file.mp4"
        return super().evaluate(expression, arg)


class QueueShimGraphFrame(StrictWaitGraphFrame):
    def __init__(self) -> None:
        super().__init__()
        self.queue_attempts = 0
        self.shim_calls = 0

    def evaluate(self, expression: str, arg: object | None = None) -> object:
        del arg
        if "_getWidgetByName" in expression:
            self.shim_calls += 1
            return 118
        if "app.queuePrompt" in expression:
            self.queue_attempts += 1
            if self.queue_attempts == 1:
                raise RuntimeError("real_node._getWidgetByName is not a function")
            return "task-123"
        return True


class QueueResponseGraphFrame(StrictWaitGraphFrame):
    def evaluate(self, expression: str, arg: object | None = None) -> object:
        del arg
        if "/task/create" in expression:
            return "task-from-create"
        if "app.queuePrompt" in expression:
            return None
        return True


class PageResponseQueueGraphFrame(StrictWaitGraphFrame):
    def evaluate(self, expression: str, arg: object | None = None) -> object:
        del expression, arg
        return None


class FakeJsonResponse:
    def __init__(self, url: str, payload: dict[str, object]) -> None:
        self.url = url
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload

    def text(self) -> str:
        return json.dumps(self._payload)


class FakeExpectResponse:
    def __init__(self, response: FakeJsonResponse) -> None:
        self.value = response

    def __enter__(self) -> "FakeExpectResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class ResponseCaptureGraphPage(FakeGraphPage):
    def __init__(self, frame: StrictWaitGraphFrame, response: FakeJsonResponse) -> None:
        super().__init__(frame)
        self._response = response
        self.expect_response_calls = 0

    def expect_response(self, matcher: object, timeout: int) -> FakeExpectResponse:
        assert callable(matcher)
        assert matcher(self._response) is True
        assert timeout > 0
        self.expect_response_calls += 1
        return FakeExpectResponse(self._response)


class ListenerQueueGraphFrame(StrictWaitGraphFrame):
    def __init__(self, emit_response: object) -> None:
        super().__init__()
        self._emit_response = emit_response

    def evaluate(self, expression: str, arg: object | None = None) -> object:
        del arg
        if "app.queuePrompt" in expression:
            self._emit_response()
            return None
        return True


class ListenerResponseGraphPage(FakeGraphPage):
    def __init__(self, response: FakeJsonResponse) -> None:
        self._listeners: list[object] = []
        self.response = response
        self.on_calls = 0
        self.remove_listener_calls = 0
        super().__init__(ListenerQueueGraphFrame(self._emit_response))

    def on(self, event_name: str, listener: object) -> None:
        assert event_name == "response"
        self._listeners.append(listener)
        self.on_calls += 1

    def remove_listener(self, event_name: str, listener: object) -> None:
        assert event_name == "response"
        self._listeners.remove(listener)
        self.remove_listener_calls += 1

    def _emit_response(self) -> None:
        for listener in list(self._listeners):
            listener(self.response)


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


def test_runninghub_adapter_pauses_when_login_button_is_visible() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(login_button_visible=True)

    result = adapter.ensure_session(page)

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


def test_runninghub_adapter_uses_first_generic_button_without_strict_mode_violation() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(
        task_id="task-123",
        has_video_input=True,
        has_image_input=True,
        has_width_input=True,
        has_height_input=True,
        strict_generic_submit_button=True,
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

    assert page.locators["button"].first.clicks == 1
    assert result.status == "submitted"
    assert result.task_id == "task-123"


def test_runninghub_adapter_loads_graph_uploads_assets_and_queues_prompt() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_api_available=True,
        graph_task_id="graph-task-123",
        graph_workflow_content={"nodes": [{"id": 57}, {"id": 63}]},
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

    assert page.graph_fetch_calls == [("2034283586668466178", "0")]
    assert page.graph_loaded_workflows == [{"nodes": [{"id": 57}, {"id": 63}]}]
    assert page.graph_uploads == [
        (63, "work/clips/clip-0001.mp4"),
        (57, "work/chatgpt_refs/clip-0001.png"),
    ]
    assert page.graph_queue_calls == [0]
    assert result.status == "submitted"
    assert result.task_id == "graph-task-123"


def test_runninghub_adapter_uploads_multiple_person_references_and_applies_lora_controls(
    tmp_path: Path,
) -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    binding_path = tmp_path / "work" / "workflow_bindings" / "wan.json"
    save_workflow_binding(
        binding_path,
        WorkflowBinding(
            workflow_id="2034283586668466178",
            video_node_id=63,
            reference_node_ids=[57, 58],
            optional_controls={"lora:jett_v1": 88},
        ),
    )
    page = FakeRunningHubPage(
        graph_api_available=True,
        graph_task_id="task-123",
        graph_workflow_content={
            "workflow_id": "2034283586668466178",
            "nodes": [
                {"id": 57, "title": "Reference Image A"},
                {"id": 58, "title": "Reference Image B"},
                {
                    "id": 63,
                    "title": "Source Video",
                    "widgets_values": {"custom_width": 1920, "custom_height": 1080},
                },
                {
                    "id": 88,
                    "title": "LoRA Jett v1",
                    "widgets_values": {"lora_name": "jett_v1", "strength_model": 0.0, "strength_clip": 0.0},
                },
            ],
        },
    )
    request = ClipExecutionRequest(
        clip_id="clip-0001",
        clip_path=Path("work/shots/clip-0001.mp4"),
        reference_image_path=Path("work/chatgpt_refs/unused.png"),
        prompt="unused",
        width=1920,
        height=1080,
        person_reference_images={
            "actor_a": Path("work/chatgpt_refs/clip-0001_actor_a.png"),
            "actor_b": Path("work/chatgpt_refs/clip-0001_actor_b.png"),
        },
        lora_controls={"jett_v1": 0.8},
        workflow_binding_path=binding_path,
    )

    result = adapter.submit_render_job(page, request)

    lora_node = next(
        node for node in page.graph_loaded_workflows[0]["nodes"] if node.get("id") == 88
    )
    assert result.status == "submitted"
    assert page.graph_uploads[0] == (63, "work/shots/clip-0001.mp4")
    assert len(page.graph_uploads) >= 3
    assert page.graph_uploads[1:] == [
        (57, "work/chatgpt_refs/clip-0001_actor_a.png"),
        (58, "work/chatgpt_refs/clip-0001_actor_b.png"),
    ]
    assert lora_node["widgets_values"]["strength_model"] == 0.8
    assert lora_node["widgets_values"]["strength_clip"] == 0.8


def test_runninghub_adapter_falls_back_to_selector_submission_when_graph_api_is_unavailable() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
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

    assert page.graph_fetch_calls == [
        ("2034283586668466178", "0")
    ] * adapter.GRAPH_READY_ATTEMPTS
    assert page.wait_for_timeout_calls == [
        adapter.GRAPH_READY_WAIT_MS
    ] * (adapter.GRAPH_READY_ATTEMPTS - 1)
    assert page.locators["#video-upload"].input_files == ["work/clips/clip-0001.mp4"]
    assert page.locators["#image-upload"].input_files == ["work/chatgpt_refs/clip-0001.png"]
    assert page.locators["button[data-testid='submit-workflow']"].clicks == 1
    assert result.status == "submitted"
    assert result.task_id == "task-123"


def test_runninghub_adapter_pauses_when_graph_queue_returns_no_task_id() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_api_available=True,
        graph_task_id=None,
        graph_workflow_content={"nodes": [{"id": 57}, {"id": 63}]},
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

    assert page.graph_fetch_calls == [("2034283586668466178", "0")]
    assert page.graph_queue_calls == [0]
    assert result.status == "paused"
    assert result.pause_reason == PauseReason.MANUAL_CONFIRMATION_REQUIRED


def test_runninghub_adapter_retries_until_graph_workflow_content_is_available() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_api_available=True,
        graph_task_id="graph-task-123",
        graph_fetch_results=[None, {"nodes": [{"id": 57}, {"id": 63}]}],
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

    assert page.graph_fetch_calls == [
        ("2034283586668466178", "0"),
        ("2034283586668466178", "0"),
    ]
    assert page.wait_for_timeout_calls == [adapter.GRAPH_READY_WAIT_MS]
    assert result.status == "submitted"
    assert result.task_id == "graph-task-123"


def test_runninghub_adapter_pauses_when_graph_workflow_token_is_invalid() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_fetch_results=[{"code": 412, "msg": "TOKEN_INVALID"}],
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

    assert page.graph_fetch_calls == [
        ("2034283586668466178", "0")
    ] * adapter.GRAPH_READY_ATTEMPTS
    assert page.wait_for_timeout_calls == [
        adapter.GRAPH_READY_WAIT_MS
    ] * (adapter.GRAPH_READY_ATTEMPTS - 1)
    assert result.status == "paused"
    assert result.pause_reason == PauseReason.LOGIN_REQUIRED


def test_runninghub_adapter_uses_cached_workflow_when_graph_api_token_is_invalid() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_task_id="graph-task-123",
        graph_fetch_results=[{"code": 412, "msg": "TOKEN_INVALID"}],
        graph_cached_workflow_content={"nodes": [{"id": 57}, {"id": 63}]},
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

    assert page.graph_fetch_calls == [("2034283586668466178", "0")]
    assert page.graph_loaded_workflows == [{"nodes": [{"id": 57}, {"id": 63}]}]
    assert page.graph_uploads == [
        (63, "work/clips/clip-0001.mp4"),
        (57, "work/chatgpt_refs/clip-0001.png"),
    ]
    assert page.graph_queue_calls == [0]
    assert result.status == "submitted"
    assert result.task_id == "graph-task-123"


def test_runninghub_adapter_retries_until_cached_workflow_is_available_after_token_invalid() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_task_id="graph-task-123",
        graph_fetch_results=[
            {"code": 412, "msg": "TOKEN_INVALID"},
            {"code": 412, "msg": "TOKEN_INVALID"},
        ],
        graph_cached_workflow_results=[
            None,
            {"nodes": [{"id": 57}, {"id": 63}]},
        ],
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

    assert page.graph_fetch_calls == [
        ("2034283586668466178", "0"),
        ("2034283586668466178", "0"),
    ]
    assert page.wait_for_timeout_calls == [adapter.GRAPH_READY_WAIT_MS]
    assert page.graph_loaded_workflows == [{"nodes": [{"id": 57}, {"id": 63}]}]
    assert result.status == "submitted"
    assert result.task_id == "graph-task-123"


def test_runninghub_adapter_retries_until_graph_loader_is_ready() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_task_id="graph-task-123",
        graph_fetch_results=[
            {"code": 412, "msg": "TOKEN_INVALID"},
            {"code": 412, "msg": "TOKEN_INVALID"},
            {"code": 412, "msg": "TOKEN_INVALID"},
        ],
        graph_cached_workflow_results=[
            {"nodes": [{"id": 57}, {"id": 63}]},
            {"nodes": [{"id": 57}, {"id": 63}]},
            {"nodes": [{"id": 57}, {"id": 63}]},
        ],
        graph_loader_ready_results=[False, False, True],
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

    assert page.graph_loader_ready_checks == 3
    assert page.wait_for_timeout_calls == [adapter.GRAPH_READY_WAIT_MS]
    assert page.graph_loaded_workflows == [{"nodes": [{"id": 57}, {"id": 63}]}]
    assert result.status == "submitted"
    assert result.task_id == "graph-task-123"


def test_runninghub_adapter_retries_longer_until_graph_loader_is_ready() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        graph_task_id="graph-task-123",
        graph_fetch_results=[{"code": 412, "msg": "TOKEN_INVALID"}] * 10,
        graph_cached_workflow_results=[{"nodes": [{"id": 57}, {"id": 63}]}] * 10,
        graph_loader_ready_results=[False] * 9 + [True],
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

    assert page.wait_for_timeout_calls == [adapter.GRAPH_READY_WAIT_MS] * 8
    assert result.status == "submitted"
    assert result.task_id == "graph-task-123"


def test_runninghub_adapter_waits_for_graph_nodes_after_graph_load() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = StrictWaitGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._load_graph_data(
        page,
        {"nodes": [{"id": 57}, {"id": 63}]},
    )

    assert result is True
    assert frame.wait_calls == [
        (
            {"nodeIds": [57, 63]},
            adapter.GRAPH_LOAD_READY_TIMEOUT_MS,
        )
    ]


def test_runninghub_adapter_uploads_graph_asset_with_keyword_wait_arg() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = StrictWaitGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._upload_graph_asset(page, 63, Path("work/clips/clip-0001.mp4"))

    assert result is True
    assert frame.file_input.input_files == ["work/clips/clip-0001.mp4"]
    assert frame.wait_calls == [
        (
            {"nodeId": 63, "previousValues": []},
            15000,
        )
    ]


def test_runninghub_adapter_upload_waits_for_graph_value_change() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = ValueChangeGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._upload_graph_asset(page, 63, Path("work/clips/clip-0001.mp4"))

    assert result is True
    assert frame.file_input.input_files == ["work/clips/clip-0001.mp4"]
    assert frame.wait_calls == [
        (
            {
                "nodeId": 63,
                "previousValues": ["existing-server-file.mp4"],
            },
            15000,
        )
    ]


def test_runninghub_adapter_returns_false_when_graph_nodes_do_not_appear_after_load() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = TimeoutLoadGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._load_graph_data(
        page,
        {"nodes": [{"id": 57}, {"id": 63}]},
    )

    assert result is False


def test_runninghub_adapter_retries_until_graph_upload_widget_is_ready() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = DelayedUploadWidgetGraphFrame(ready_on_attempt=3)
    page = FakeGraphPage(frame)

    result = adapter._upload_graph_asset(page, 63, Path("work/clips/clip-0001.mp4"))

    assert result is True
    assert page.wait_for_timeout_calls == [
        adapter.GRAPH_READY_WAIT_MS,
        adapter.GRAPH_READY_WAIT_MS,
    ]
    assert frame.file_input.input_files == ["work/clips/clip-0001.mp4"]
    assert frame.wait_calls == [
        (
            {
                "nodeId": 63,
                "previousValues": ["existing-server-file.mp4"],
            },
            15000,
        )
    ]


def test_runninghub_adapter_uploads_graph_asset_via_api_fallback_after_wait_timeout() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = ApiFallbackGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._upload_graph_asset(page, 63, Path("work/clips/clip-0001.mp4"))

    assert result is True
    assert frame.api_file_input.input_files == ["work/clips/clip-0001.mp4"]
    assert frame.api_upload_args == [{"nodeId": 63}]


def test_runninghub_adapter_retries_queue_after_injecting_get_widget_shim() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = QueueShimGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._queue_graph_prompt(page, adapter.GRAPH_PROMPT_NUMBER)

    assert result == "task-123"
    assert frame.shim_calls == 1


def test_runninghub_adapter_reads_task_id_from_task_create_response() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = QueueResponseGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._queue_graph_prompt(page, adapter.GRAPH_PROMPT_NUMBER)

    assert result == "task-from-create"


def test_runninghub_adapter_reads_task_id_from_page_task_create_response() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = PageResponseQueueGraphFrame()
    page = ResponseCaptureGraphPage(
        frame,
        FakeJsonResponse(
            "https://www.runninghub.cn/task/create",
            {"code": 0, "data": {"taskId": "task-from-page-response"}},
        ),
    )

    result = adapter._queue_graph_prompt(page, adapter.GRAPH_PROMPT_NUMBER)

    assert result == "task-from-page-response"
    assert page.expect_response_calls == 1


def test_runninghub_adapter_reads_task_id_from_response_listener_capture() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = ListenerResponseGraphPage(
        FakeJsonResponse(
            "https://www.runninghub.cn/task/create",
            {"code": 0, "data": {"taskId": "task-from-listener"}},
        )
    )

    result = adapter._queue_graph_prompt(page, adapter.GRAPH_PROMPT_NUMBER)

    assert result == "task-from-listener"
    assert page.on_calls == 1
    assert page.remove_listener_calls == 1


def test_runninghub_adapter_returns_false_when_graph_load_raises() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = ErrorGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._load_graph_data(page, {"nodes": []})

    assert result is False


def test_runninghub_adapter_returns_false_when_graph_upload_wait_times_out() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    frame = TimeoutGraphFrame()
    page = FakeGraphPage(frame)

    result = adapter._upload_graph_asset(page, 63, Path("work/clips/clip-0001.mp4"))

    assert result is False


def test_runninghub_adapter_reads_running_task_status() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(task_status="running", task_id="task-123")

    result = adapter.poll_render_status(page=page, task_id="task-123")

    assert result.status == RunningHubTaskStatus.RUNNING
    assert result.task_id == "task-123"
    assert result.pause_reason is None


def test_runninghub_adapter_uses_authenticated_task_list_when_dom_status_is_pending() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        task_id="task-123",
        task_status="pending",
        task_list_records=[
            {
                "taskId": "task-123",
                "taskStatus": "SUCCESS",
            }
        ],
    )

    result = adapter.poll_render_status(page=page, task_id="task-123")

    assert page.fetch_runninghub_task_list_calls == 1
    assert result.status == RunningHubTaskStatus.DONE
    assert result.task_id == "task-123"
    assert result.pause_reason is None


def test_runninghub_adapter_retries_task_list_until_matching_record_appears() -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    page = FakeRunningHubPage(
        task_id="task-123",
        task_status="pending",
        task_list_results=[
            [],
            [{"taskId": "task-123", "taskStatus": "SUCCESS"}],
        ],
    )

    result = adapter.poll_render_status(page=page, task_id="task-123")

    assert page.fetch_runninghub_task_list_calls == 2
    assert page.wait_for_timeout_calls == [adapter.GRAPH_READY_WAIT_MS]
    assert result.status == RunningHubTaskStatus.DONE


def test_runninghub_adapter_downloads_rendered_file_when_done(tmp_path: Path) -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    output_path = tmp_path / "output" / "rendered" / "clip-0001.mp4"
    source_path = tmp_path / "downloads" / "downloaded.mp4"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"video-bytes")
    page = FakeRunningHubPage(task_status="done", downloadable_path=source_path)

    result = adapter.download_render_output(page=page, output_path=output_path)

    assert output_path.exists() is True
    assert output_path.read_bytes() == b"video-bytes"
    assert page.locators["button[data-testid='download-render']"].clicks == 1
    assert result.status == "downloaded"
    assert result.output_path == output_path


def test_runninghub_adapter_pauses_when_download_button_is_missing(tmp_path: Path) -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(has_download_button=False)

    result = adapter.download_render_output(
        page=page,
        output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
    )

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.SELECTOR_MISSING


def test_runninghub_adapter_extracts_identify_from_plain_hash() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")

    result = adapter._extract_identify_from_text("af2333a12b55a3e9680bd2ed0ec6a8b3")

    assert result == "af2333a12b55a3e9680bd2ed0ec6a8b3"


def test_runninghub_adapter_downloads_media_url_from_matching_task_card_when_button_is_missing(
    tmp_path: Path,
) -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    output_path = tmp_path / "output" / "rendered" / "clip-0001.mp4"
    page = FakeRunningHubPage(
        has_download_button=False,
        task_media_urls={
            "task-123": (
                "https://rh-images.xiaoyaoyou.com/identify/output/"
                "WanAnimate_00001.mp4"
            )
        },
    )

    result = adapter.download_render_output(
        page=page,
        output_path=output_path,
        task_id="task-123",
    )

    assert page.read_task_media_url_calls == ["task-123"]
    assert page.download_url_calls == [
        (
            "https://rh-images.xiaoyaoyou.com/identify/output/WanAnimate_00001.mp4",
            output_path.as_posix(),
        )
    ]
    assert output_path.exists() is True
    assert result.status == "downloaded"
    assert result.output_path == output_path


def test_runninghub_adapter_retries_media_url_lookup_until_task_card_is_rendered(
    tmp_path: Path,
) -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    output_path = tmp_path / "output" / "rendered" / "clip-0001.mp4"
    page = FakeRunningHubPage(
        has_download_button=False,
        task_media_results=[
            None,
            "https://rh-images.xiaoyaoyou.com/identify/output/WanAnimate_00001.mp4",
        ],
    )

    result = adapter.download_render_output(
        page=page,
        output_path=output_path,
        task_id="task-123",
    )

    assert page.read_task_media_url_calls == ["task-123", "task-123"]
    assert page.wait_for_timeout_calls == [adapter.GRAPH_READY_WAIT_MS]
    assert result.status == "downloaded"
    assert result.output_path == output_path


def test_runninghub_adapter_downloads_from_output_history_when_task_card_media_is_missing(
    tmp_path: Path,
) -> None:
    adapter = RunningHubPageAdapter(
        workflow_url="https://www.runninghub.cn/workflow/2034283586668466178"
    )
    output_path = tmp_path / "output" / "rendered" / "clip-0001.mp4"
    page = FakeRunningHubPage(
        has_download_button=False,
        output_history_records=[
            {
                "taskId": "task-123",
                "fileUrl": "https://rh-images.xiaoyaoyou.com/identify/output/WanAnimate_00001.mp4",
            }
        ],
    )

    result = adapter.download_render_output(
        page=page,
        output_path=output_path,
        task_id="task-123",
    )

    assert page.fetch_runninghub_output_history_calls == 1
    assert page.download_url_calls == [
        (
            "https://rh-images.xiaoyaoyou.com/identify/output/WanAnimate_00001.mp4",
            output_path.as_posix(),
        )
    ]
    assert result.status == "downloaded"
    assert result.output_path == output_path
