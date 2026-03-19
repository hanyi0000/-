from pathlib import Path

from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.live_state import (
    LiveClipState,
    PauseReason,
    load_live_state,
    save_live_state,
)
from scripts.browser_video_remix.paths import build_project_paths
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


class FakeLocator:
    def __init__(
        self,
        *,
        count: int = 0,
        visible: bool = False,
        text: str = "",
        screenshot_bytes: bytes | None = None,
    ) -> None:
        self._count = count
        self._visible = visible
        self._text = text
        self.input_files: list[str] = []
        self.filled_values: list[str] = []
        self.clicks = 0
        self.screenshot_bytes = screenshot_bytes

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

    def screenshot(self, path: str) -> None:
        if self.screenshot_bytes is None:
            raise RuntimeError("screenshot bytes not configured")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.screenshot_bytes)


class FakeChatGptPage:
    def __init__(self) -> None:
        self.goto_calls: list[tuple[str, str]] = []
        self.locators = {
            "#upload-files": FakeLocator(count=1),
            "#upload-photos": FakeLocator(count=1),
            "textarea[name='prompt-textarea']": FakeLocator(count=1, visible=True),
            "[data-message-author-role='assistant'] img": FakeLocator(
                count=1,
                visible=True,
                screenshot_bytes=b"generated-reference-image",
            ),
            "[data-testid='send-button']": FakeLocator(count=1, visible=True),
        }

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())

    def get_by_role(self, role: str, name: str) -> FakeLocator:
        return FakeLocator()

    def get_by_text(self, text: str) -> FakeLocator:
        if text.endswith(".png"):
            return FakeLocator(count=1, visible=True)
        return FakeLocator()

    def wait_for_function(
        self,
        expression: str,
        arg: object | None = None,
        timeout: object | None = None,
    ) -> None:
        del expression, arg, timeout


class FakeRunningHubPage:
    def __init__(
        self,
        task_id: str = "task-123",
        task_status: str = "done",
        downloadable_path: Path | None = None,
    ) -> None:
        self.task_id = task_id
        self.goto_calls: list[tuple[str, str]] = []
        self.task_status = task_status
        self.downloadable_path = downloadable_path
        if self.downloadable_path is not None:
            self.downloadable_path.parent.mkdir(parents=True, exist_ok=True)
            self.downloadable_path.write_bytes(b"video-bytes")
        self.locators = {
            "#video-upload": FakeLocator(count=1),
            "#image-upload": FakeLocator(count=1),
            "input[name='width']": FakeLocator(count=1, visible=True),
            "input[name='height']": FakeLocator(count=1, visible=True),
            "button[data-testid='submit-workflow']": FakeLocator(count=1, visible=True),
            "button[data-testid='download-render']": FakeLocator(count=1, visible=True),
            "[data-testid='task-id']": FakeLocator(count=1, visible=True, text=task_id),
            "[data-testid='task-status']": FakeLocator(
                count=1,
                visible=True,
                text=task_status,
            ),
        }

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())

    def expect_download(self) -> object:
        if self.downloadable_path is None:
            raise RuntimeError("downloadable_path not configured")
        page = self

        class FakeDownload:
            def save_as(self, target_path: str) -> None:
                target = Path(target_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(page.downloadable_path.read_bytes())

        class FakeExpectDownload:
            def __init__(self) -> None:
                self.value = FakeDownload()

            def __enter__(self) -> "FakeExpectDownload":
                return self

            def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
                return False

        return FakeExpectDownload()


class FakeChatGptAdapter:
    def __init__(self) -> None:
        self.submit_calls = 0

    def submit_reference_generation(self, page: object, request: object) -> object:
        del page, request
        self.submit_calls += 1
        return type(
            "Result",
            (),
            {
                "status": "completed",
                "output_path": Path("work/chatgpt_refs/clip-0001.png"),
                "pause_reason": None,
            },
        )()


class FakeRunningHubAdapter:
    def __init__(
        self,
        *,
        submit_result: dict[str, object] | None = None,
        poll_result: dict[str, object] | None = None,
        download_result: dict[str, object] | None = None,
    ) -> None:
        self.submit_calls = 0
        self.poll_calls = 0
        self.download_calls = 0
        self.download_task_ids: list[str | None] = []
        self.ensure_session_calls = 0
        self.snapshot_calls = 0
        self._submit_result = submit_result or {
            "status": "submitted",
            "task_id": "task-123",
            "pause_reason": None,
        }
        self._poll_result = poll_result or {
            "status": "done",
            "task_id": "task-123",
            "pause_reason": None,
        }
        self._download_result = download_result or {
            "status": "downloaded",
            "output_path": None,
            "pause_reason": None,
        }

    def ensure_session(self, page: object) -> object:
        del page
        self.ensure_session_calls += 1
        return type(
            "Result",
            (),
            {
                "status": "ready",
                "task_id": None,
                "pause_reason": None,
            },
        )()

    def submit_render_job(self, page: object, request: object) -> object:
        del page, request
        self.submit_calls += 1
        return type("Result", (), self._submit_result)()

    def poll_render_status(self, page: object, task_id: str) -> object:
        del page, task_id
        self.poll_calls += 1
        return type("Result", (), self._poll_result)()

    def download_render_output(
        self,
        page: object,
        output_path: Path,
        task_id: str | None = None,
    ) -> object:
        del page
        self.download_calls += 1
        self.download_task_ids.append(task_id)
        if self._download_result["status"] == "downloaded":
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"video-bytes")
        payload = dict(self._download_result)
        if payload.get("output_path") is None and payload["status"] == "downloaded":
            payload["output_path"] = output_path
        return type("Result", (), payload)()

    def capture_failure_snapshot(
        self,
        page: object,
        screenshot_path: Path,
        html_path: Path,
        summary_path: Path,
    ) -> None:
        del page
        self.snapshot_calls += 1
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(b"png-bytes")
        html_path.write_text("<html>pause</html>", encoding="utf-8")
        summary_path.write_text('{"status":"paused"}', encoding="utf-8")


class FakePausedChatGptAdapter:
    def submit_reference_generation(self, page: object, request: object) -> object:
        return type(
            "Result",
            (),
            {
                "status": "paused",
                "output_path": None,
                "pause_reason": PauseReason.LOGIN_REQUIRED,
            },
        )()


def test_run_single_clip_live_flow_returns_state_path_and_task_id(
    tmp_path: Path,
) -> None:
    result = run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=tmp_path / "work" / "live_state" / "clip-0001.json",
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
        ),
        chatgpt_page=object(),
        runninghub_page=object(),
        chatgpt_adapter=FakeChatGptAdapter(),
        runninghub_adapter=FakeRunningHubAdapter(),
    )

    assert result["clip_id"] == "clip-0001"
    assert result["task_id"] == "task-123"
    assert result["state_path"].endswith("clip-0001.json")


def test_run_single_clip_live_flow_builds_adapter_requests_for_real_adapters(
    tmp_path: Path,
) -> None:
    downloadable_path = tmp_path / "work" / "downloads" / "rendered.mp4"
    result = run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=tmp_path / "work" / "live_state" / "clip-0001.json",
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
        ),
        chatgpt_page=FakeChatGptPage(),
        runninghub_page=FakeRunningHubPage(downloadable_path=downloadable_path),
        chatgpt_adapter=ChatGptPageAdapter(start_url="https://chatgpt.com/g/test"),
        runninghub_adapter=RunningHubPageAdapter(workflow_url="https://example.com/workflow"),
    )

    assert result["reference_image_path"].endswith("chatgpt_refs/clip-0001.png")


def test_run_single_clip_live_flow_stops_before_runninghub_when_chatgpt_pauses(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "work" / "live_state" / "clip-0001.json"
    runninghub_adapter = FakeRunningHubAdapter()

    result = run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=state_path,
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
        ),
        chatgpt_page=object(),
        runninghub_page=object(),
        chatgpt_adapter=FakePausedChatGptAdapter(),
        runninghub_adapter=runninghub_adapter,
    )

    saved_state = load_live_state(state_path)

    assert runninghub_adapter.submit_calls == 0
    assert result["task_id"] == ""
    assert saved_state.step == "paused"
    assert saved_state.pause_reason == PauseReason.LOGIN_REQUIRED


def test_run_single_clip_live_flow_polls_and_downloads_after_submit(
    tmp_path: Path,
) -> None:
    rendered_output_path = tmp_path / "output" / "rendered" / "clip-0001.mp4"
    runninghub_adapter = FakeRunningHubAdapter(
        submit_result={"status": "submitted", "task_id": "task-123", "pause_reason": None},
        poll_result={"status": "done", "task_id": "task-123", "pause_reason": None},
        download_result={
            "status": "downloaded",
            "output_path": rendered_output_path,
            "pause_reason": None,
        },
    )

    result = run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=tmp_path / "work" / "live_state" / "clip-0001.json",
            rendered_output_path=rendered_output_path,
        ),
        chatgpt_page=object(),
        runninghub_page=object(),
        chatgpt_adapter=FakeChatGptAdapter(),
        runninghub_adapter=runninghub_adapter,
    )

    assert runninghub_adapter.submit_calls == 1
    assert runninghub_adapter.poll_calls == 1
    assert runninghub_adapter.download_calls == 1
    assert runninghub_adapter.download_task_ids == ["task-123"]
    assert result["task_id"] == "task-123"


def test_run_single_clip_live_flow_resumes_polling_without_resubmitting(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "work" / "live_state" / "clip-0001.json"
    save_live_state(
        state_path,
        LiveClipState(
            clip_id="clip-0001",
            step="runninghub_submitted",
            reference_image_path=tmp_path / "work" / "chatgpt_refs" / "clip-0001.png",
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
            runninghub_task_id="task-123",
            pause_reason=None,
            last_error=None,
            last_screenshot_path=None,
        ),
    )
    runninghub_adapter = FakeRunningHubAdapter(
        submit_result={"status": "submitted", "task_id": "task-999", "pause_reason": None},
        poll_result={"status": "done", "task_id": "task-123", "pause_reason": None},
        download_result={
            "status": "downloaded",
            "output_path": tmp_path / "output" / "rendered" / "clip-0001.mp4",
            "pause_reason": None,
        },
    )

    run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=state_path,
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
        ),
        chatgpt_page=object(),
        runninghub_page=object(),
        chatgpt_adapter=FakeChatGptAdapter(),
        runninghub_adapter=runninghub_adapter,
    )

    assert runninghub_adapter.submit_calls == 0
    assert runninghub_adapter.poll_calls == 1


def test_run_single_clip_live_flow_reuses_existing_reference_image_on_resume(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "work" / "live_state" / "clip-0001.json"
    reference_image_path = tmp_path / "work" / "chatgpt_refs" / "clip-0001.png"
    reference_image_path.parent.mkdir(parents=True, exist_ok=True)
    reference_image_path.write_bytes(b"reference-bytes")
    save_live_state(
        state_path,
        LiveClipState(
            clip_id="clip-0001",
            step="runninghub_polling",
            reference_image_path=reference_image_path,
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
            runninghub_task_id="task-123",
            pause_reason=None,
            last_error=None,
            last_screenshot_path=None,
        ),
    )
    chatgpt_adapter = FakeChatGptAdapter()
    runninghub_adapter = FakeRunningHubAdapter(
        poll_result={"status": "running", "task_id": "task-123", "pause_reason": None},
    )

    result = run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=state_path,
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
        ),
        chatgpt_page=object(),
        runninghub_page=object(),
        chatgpt_adapter=chatgpt_adapter,
        runninghub_adapter=runninghub_adapter,
    )

    assert chatgpt_adapter.submit_calls == 0
    assert runninghub_adapter.ensure_session_calls == 1
    assert runninghub_adapter.submit_calls == 0
    assert runninghub_adapter.poll_calls == 1
    assert result["task_id"] == "task-123"
    assert result["reference_image_path"] == reference_image_path.as_posix()


def test_run_single_clip_live_flow_saves_runninghub_pause_artifacts(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "work" / "live_state" / "clip-0001.json"
    runninghub_adapter = FakeRunningHubAdapter(
        submit_result={
            "status": "paused",
            "task_id": None,
            "pause_reason": PauseReason.SELECTOR_MISSING,
        },
    )

    run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="clip-0001",
            clip_path=tmp_path / "work" / "clips" / "clip-0001.mp4",
            frame_path=tmp_path / "work" / "frames" / "clip-0001.png",
            prompt="replace actor_a with jett",
            state_path=state_path,
            rendered_output_path=tmp_path / "output" / "rendered" / "clip-0001.mp4",
        ),
        chatgpt_page=object(),
        runninghub_page=object(),
        chatgpt_adapter=FakeChatGptAdapter(),
        runninghub_adapter=runninghub_adapter,
    )

    pause_dir = build_project_paths(tmp_path).runninghub_pauses_dir / "clip-0001"
    saved_state = load_live_state(state_path)

    assert runninghub_adapter.snapshot_calls == 1
    assert saved_state.pause_reason == PauseReason.SELECTOR_MISSING
    assert saved_state.last_screenshot_path == pause_dir / "pause.png"
    assert saved_state.last_screenshot_path.exists() is True
    assert (pause_dir / "pause.html").exists() is True
    assert (pause_dir / "pause.json").exists() is True
