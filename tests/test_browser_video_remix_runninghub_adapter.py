from scripts.browser_video_remix.browser_executor import (
    RunningHubTaskStatus,
    is_terminal_runninghub_state,
)


def test_is_terminal_runninghub_state_accepts_done_and_failed() -> None:
    assert is_terminal_runninghub_state(RunningHubTaskStatus.DONE) is True
    assert is_terminal_runninghub_state(RunningHubTaskStatus.FAILED) is True
    assert is_terminal_runninghub_state(RunningHubTaskStatus.RUNNING) is False
