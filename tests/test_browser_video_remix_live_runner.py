from pathlib import Path

from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.live_state import PauseReason, load_live_state
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


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


class FakeChatGptPage:
    def __init__(self) -> None:
        self.goto_calls: list[tuple[str, str]] = []
        self.locators = {
            "#upload-files": FakeLocator(count=1),
            "textarea[name='prompt-textarea']": FakeLocator(count=1),
        }

    def goto(self, url: str, wait_until: str) -> None:
        self.goto_calls.append((url, wait_until))

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator())

    def get_by_role(self, role: str, name: str) -> FakeLocator:
        return FakeLocator()

    def get_by_text(self, text: str) -> FakeLocator:
        return FakeLocator()


class FakeChatGptAdapter:
    def submit_reference_generation(self, page: object, request: object) -> object:
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
    def __init__(self) -> None:
        self.calls = 0

    def submit_render_job(self, page: object, request: object) -> object:
        self.calls += 1
        return type(
            "Result",
            (),
            {"status": "submitted", "task_id": "task-123", "pause_reason": None},
        )()


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
        runninghub_page=type("Page", (), {"task_id": "task-123"})(),
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

    assert runninghub_adapter.calls == 0
    assert result["task_id"] == ""
    assert saved_state.step == "paused"
    assert saved_state.pause_reason == PauseReason.LOGIN_REQUIRED
