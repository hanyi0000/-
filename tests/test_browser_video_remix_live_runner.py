from pathlib import Path

from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


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
    def submit_render_job(self, page: object, request: object) -> object:
        return type(
            "Result",
            (),
            {"status": "submitted", "task_id": "task-123", "pause_reason": None},
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
        chatgpt_page=object(),
        runninghub_page=type("Page", (), {"task_id": "task-123"})(),
        chatgpt_adapter=ChatGptPageAdapter(start_url="https://chatgpt.com/g/test"),
        runninghub_adapter=RunningHubPageAdapter(workflow_url="https://example.com/workflow"),
    )

    assert result["reference_image_path"].endswith("chatgpt_refs/clip-0001.png")
