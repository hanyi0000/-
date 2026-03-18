from pathlib import Path

from scripts.browser_video_remix.browser_executor import ChatGptReferenceRequest
from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_state import PauseReason


class FakeChatGptPage:
    def __init__(self, login_required: bool = False) -> None:
        self.login_required = login_required


def test_chatgpt_adapter_pauses_when_login_is_required() -> None:
    adapter = ChatGptPageAdapter(start_url="https://chatgpt.com/g/test")
    result = adapter.submit_reference_generation(
        page=FakeChatGptPage(login_required=True),
        request=ChatGptReferenceRequest(
            clip_id="clip-0001",
            frame_path=Path("work/frames/clip-0001.png"),
            output_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
        ),
    )

    assert result.status == "paused"
    assert result.pause_reason == PauseReason.LOGIN_REQUIRED


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
