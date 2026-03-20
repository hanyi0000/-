from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
    ClipExecutionRequest,
    RunningHubDownloadResult,
    RunningHubPollResult,
    RunningHubTaskStatus,
    is_terminal_runninghub_state,
)


def test_runninghub_poll_result_tracks_status_and_task_id() -> None:
    result = RunningHubPollResult(
        status=RunningHubTaskStatus.RUNNING,
        task_id="task-123",
        pause_reason=None,
    )

    assert result.status == RunningHubTaskStatus.RUNNING
    assert result.task_id == "task-123"
    assert result.pause_reason is None


def test_runninghub_download_result_tracks_output_path() -> None:
    output_path = Path("output/rendered/clip-0001.mp4")
    result = RunningHubDownloadResult(
        status="downloaded",
        output_path=output_path,
        pause_reason=None,
    )

    assert result.status == "downloaded"
    assert result.output_path == output_path
    assert result.pause_reason is None


def test_is_terminal_runninghub_state_accepts_done_and_failed() -> None:
    assert is_terminal_runninghub_state(RunningHubTaskStatus.DONE) is True
    assert is_terminal_runninghub_state(RunningHubTaskStatus.FAILED) is True
    assert is_terminal_runninghub_state(RunningHubTaskStatus.RUNNING) is False


def test_clip_execution_request_supports_multiperson_controls() -> None:
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
        workflow_binding_path=Path("work/workflow_bindings/wan.json"),
    )

    assert sorted(request.person_reference_images) == ["actor_a", "actor_b"]
    assert request.lora_controls["jett_v1"] == 0.8
    assert request.workflow_binding_path.as_posix().endswith("wan.json")
