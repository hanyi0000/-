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
