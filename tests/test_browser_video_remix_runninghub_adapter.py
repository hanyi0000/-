from pathlib import Path

from scripts.browser_video_remix.browser_executor import (
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
