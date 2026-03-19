# RunningHub Live Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the single-clip live browser flow through RunningHub submission, polling, download, and resume-safe state progression.

**Architecture:** Extend the existing `RunningHubPageAdapter` from a stub into a staged real browser adapter, then teach the live runner to persist `task_id`, resume from polling instead of resubmitting, and validate the downloaded render before marking the clip done. Keep all UI drift isolated to the adapter and all sequencing/persistence isolated to the runner.

**Tech Stack:** Python 3, Playwright sync API, pytest, PyYAML

---

### Task 1: Implement real RunningHub session check and workflow submission

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path

from scripts.browser_video_remix.browser_executor import ClipExecutionRequest
from scripts.browser_video_remix.live_state import PauseReason
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


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

    assert page.locators["#video-upload"].input_files == ["work/clips/clip-0001.mp4"]
    assert page.locators["#image-upload"].input_files == ["work/chatgpt_refs/clip-0001.png"]
    assert page.locators["input[name='width']"].filled_values[-1] == "1920"
    assert page.locators["input[name='height']"].filled_values[-1] == "1080"
    assert page.locators["button[data-testid='submit-workflow']"].clicks == 1
    assert result.status == "submitted"
    assert result.task_id == "task-123"
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py -q`

Expected: FAIL because the current adapter only returns `page.task_id` and does not perform session checks, uploads, field writes, or submission clicks.

**Step 3: Write the minimal implementation**

```python
class RunningHubPageAdapter:
    VIDEO_INPUT_SELECTORS = ("#video-upload", "input[type='file'][accept*='video']")
    IMAGE_INPUT_SELECTORS = ("#image-upload", "input[type='file'][accept*='image']")
    WIDTH_INPUT_SELECTORS = ("input[name='width']", "#width")
    HEIGHT_INPUT_SELECTORS = ("input[name='height']", "#height")
    SUBMIT_BUTTON_SELECTORS = ("button[data-testid='submit-workflow']", "button")
    TASK_ID_SELECTORS = ("[data-testid='task-id']", "[data-task-id]")

    def ensure_session(self, page: object) -> RunningHubSubmitResult:
        page.goto(self.workflow_url, wait_until="domcontentloaded")
        if getattr(page, "login_required", False):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return RunningHubSubmitResult(status="ready", task_id=None, pause_reason=None)

    def submit_render_job(self, page: object, request: ClipExecutionRequest) -> RunningHubSubmitResult:
        session = self.ensure_session(page)
        if session.pause_reason is not None:
            return session

        video_input = self._find_first_available_locator(page, self.VIDEO_INPUT_SELECTORS)
        image_input = self._find_first_available_locator(page, self.IMAGE_INPUT_SELECTORS)
        width_input = self._find_first_available_locator(page, self.WIDTH_INPUT_SELECTORS)
        height_input = self._find_first_available_locator(page, self.HEIGHT_INPUT_SELECTORS)
        submit_button = self._find_first_available_locator(page, self.SUBMIT_BUTTON_SELECTORS)
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
        return RunningHubSubmitResult(status="submitted", task_id=task_id, pause_reason=None)
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/runninghub_page.py tests/test_browser_video_remix_runninghub_page.py
git commit -m "feat: implement runninghub workflow submission"
```

### Task 2: Add RunningHub polling and download results to the adapter

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path

from scripts.browser_video_remix.browser_executor import RunningHubTaskStatus
from scripts.browser_video_remix.live_state import PauseReason
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


def test_runninghub_adapter_reads_running_task_status() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    page = FakeRunningHubPage(task_status="running", task_id="task-123")

    result = adapter.poll_render_status(page=page, task_id="task-123")

    assert result.status == RunningHubTaskStatus.RUNNING
    assert result.task_id == "task-123"
    assert result.pause_reason is None


def test_runninghub_adapter_downloads_rendered_file_when_done(tmp_path: Path) -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    output_path = tmp_path / "output" / "rendered" / "clip-0001.mp4"
    page = FakeRunningHubPage(task_status="done", downloadable_path=tmp_path / "downloaded.mp4")

    result = adapter.download_render_output(page=page, output_path=output_path)

    assert output_path.exists() is True
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
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py -q`

Expected: FAIL because the adapter has no polling or download methods and `browser_executor.py` has no poll/download result models.

**Step 3: Write the minimal implementation**

```python
@dataclass(frozen=True)
class RunningHubPollResult:
    status: RunningHubTaskStatus
    task_id: str
    pause_reason: PauseReason | None


@dataclass(frozen=True)
class RunningHubDownloadResult:
    status: str
    output_path: Path | None
    pause_reason: PauseReason | None


def poll_render_status(self, page: object, task_id: str) -> RunningHubPollResult:
    status_text = self._read_task_status_text(page, task_id).lower()
    if status_text == "done":
        return RunningHubPollResult(RunningHubTaskStatus.DONE, task_id, None)
    if status_text == "failed":
        return RunningHubPollResult(RunningHubTaskStatus.FAILED, task_id, None)
    if status_text == "running":
        return RunningHubPollResult(RunningHubTaskStatus.RUNNING, task_id, None)
    return RunningHubPollResult(RunningHubTaskStatus.PENDING, task_id, None)


def download_render_output(self, page: object, output_path: Path) -> RunningHubDownloadResult:
    download_button = self._find_first_available_locator(page, self.DOWNLOAD_BUTTON_SELECTORS)
    if download_button is None:
        return RunningHubDownloadResult("paused", None, PauseReason.SELECTOR_MISSING)

    download = page.expect_download()
    with download as pending_download:
        download_button.click()
    pending_download.value.save_as(output_path.as_posix())
    if not output_path.exists() or output_path.stat().st_size <= 0:
        return RunningHubDownloadResult("failed", None, PauseReason.MANUAL_CONFIRMATION_REQUIRED)
    return RunningHubDownloadResult("downloaded", output_path, None)
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/browser_executor.py scripts/browser_video_remix/runninghub_page.py tests/test_browser_video_remix_runninghub_adapter.py tests/test_browser_video_remix_runninghub_page.py
git commit -m "feat: add runninghub polling and download flow"
```

### Task 3: Extend the live runner to persist RunningHub progress and resume from task ID

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_state.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py`

**Step 1: Write the failing tests**

```python
from pathlib import Path

from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.live_state import LiveClipState, save_live_state


def test_run_single_clip_live_flow_polls_and_downloads_after_submit(tmp_path: Path) -> None:
    runninghub_adapter = FakeRunningHubAdapter(
        submit_result={"status": "submitted", "task_id": "task-123", "pause_reason": None},
        poll_result={"status": "done", "task_id": "task-123", "pause_reason": None},
        download_result={"status": "downloaded", "output_path": tmp_path / "output" / "rendered" / "clip-0001.mp4", "pause_reason": None},
    )

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
        runninghub_adapter=runninghub_adapter,
    )

    assert runninghub_adapter.submit_calls == 1
    assert runninghub_adapter.poll_calls == 1
    assert runninghub_adapter.download_calls == 1
    assert result["task_id"] == "task-123"


def test_run_single_clip_live_flow_resumes_polling_without_resubmitting(tmp_path: Path) -> None:
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
        download_result={"status": "downloaded", "output_path": tmp_path / "output" / "rendered" / "clip-0001.mp4", "pause_reason": None},
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
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py -q`

Expected: FAIL because the live runner currently stops after `submit_render_job()` and never loads existing state to resume polling.

**Step 3: Write the minimal implementation**

```python
def run_single_clip_live_flow(...):
    existing_state = load_live_state(request.state_path) if request.state_path.exists() else None

    reference_result = chatgpt_adapter.submit_reference_generation(...)
    if reference_result.pause_reason is not None:
        ...

    task_id = None
    if existing_state is not None and existing_state.runninghub_task_id:
        task_id = existing_state.runninghub_task_id
    else:
        runninghub_result = runninghub_adapter.submit_render_job(runninghub_page, runninghub_request)
        if runninghub_result.pause_reason is not None:
            ...
        task_id = runninghub_result.task_id
        save_live_state(... step="runninghub_submitted", runninghub_task_id=task_id ...)

    poll_result = runninghub_adapter.poll_render_status(runninghub_page, task_id)
    if poll_result.pause_reason is not None:
        ...
    save_live_state(... step="runninghub_polling", runninghub_task_id=task_id ...)

    if poll_result.status == RunningHubTaskStatus.FAILED:
        save_live_state(... step="failed", runninghub_task_id=task_id ...)
        return ...

    download_result = runninghub_adapter.download_render_output(
        runninghub_page,
        request.rendered_output_path,
    )
    if download_result.pause_reason is not None:
        ...
    save_live_state(... step="done", runninghub_task_id=task_id ...)
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/live_runner.py scripts/browser_video_remix/live_state.py tests/test_browser_video_remix_live_runner.py
git commit -m "feat: persist runninghub progress in live runner"
```

### Task 4: Capture RunningHub pause evidence and update smoke-test documentation

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\paths.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.live_state import load_live_state, PauseReason


def test_run_single_clip_live_flow_saves_runninghub_pause_artifacts(tmp_path: Path) -> None:
    state_path = tmp_path / "work" / "live_state" / "clip-0001.json"
    runninghub_adapter = FakeRunningHubAdapter(
        submit_result={"status": "paused", "task_id": None, "pause_reason": PauseReason.SELECTOR_MISSING},
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

    saved_state = load_live_state(state_path)
    assert saved_state.pause_reason == PauseReason.SELECTOR_MISSING
    assert saved_state.last_screenshot_path is not None
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py -k runninghub_pause_artifacts -q`

Expected: FAIL because the live runner currently saves pause state without RunningHub screenshots, HTML, or JSON evidence.

**Step 3: Write the minimal implementation**

```python
def capture_failure_snapshot(self, page: object, screenshot_path: Path, html_path: Path, summary_path: Path) -> None:
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=screenshot_path.as_posix(), full_page=True)
    html_path.write_text(page.content(), encoding="utf-8")
    summary_path.write_text(
        json.dumps({"url": page.url, "title": page.title()}, indent=2),
        encoding="utf-8",
    )


pause_dir = build_project_paths(request.state_path.parents[2]).logs_dir / "runninghub-pauses" / request.clip_id
runninghub_adapter.capture_failure_snapshot(
    runninghub_page,
    pause_dir / "pause.png",
    pause_dir / "pause.html",
    pause_dir / "pause.json",
)
save_live_state(... last_screenshot_path=pause_dir / "pause.png")
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add docs/browser-video-remix-smoke-test.md scripts/browser_video_remix/live_runner.py scripts/browser_video_remix/paths.py scripts/browser_video_remix/runninghub_page.py tests/test_browser_video_remix_live_runner.py
git commit -m "docs: add runninghub live smoke and pause evidence"
```

### Task 5: Run real single-clip smoke verification

**Files:**
- Verify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\chatgpt_page.py`
- Verify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- Verify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_runner.py`
- Verify: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`

**Step 1: Run the full automated test suite**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with pyyaml pytest D:\codex-worktrees\browser-video-remix-phase2\tests -q`

Expected: PASS with zero failures.

**Step 2: Run one real authenticated clip through ChatGPT and RunningHub**

Run:

```powershell
$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'
@'
from pathlib import Path
from playwright.sync_api import sync_playwright

from scripts.browser_video_remix.browser_executor import ChatGptReferenceRequest
from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.playwright_driver import PersistentContextRequest, launch_persistent_context
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter

repo = Path(r"D:\codex-worktrees\browser-video-remix-phase2")
with sync_playwright() as p:
    context = launch_persistent_context(
        p,
        PersistentContextRequest(
            profile_dir=repo / "browser" / "edge-proxy-smoke-profile",
            downloads_dir=repo / "work" / "downloads",
            default_timeout_ms=20000,
            headless=False,
            executable_path=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            proxy_server="socks5://127.0.0.1:1080",
        ),
    )
    chatgpt_page = context.new_page()
    runninghub_page = context.new_page()
    result = run_single_clip_live_flow(
        request=LiveClipRequest(
            clip_id="smoke-live",
            clip_path=repo / "work" / "clips" / "smoke-live.mp4",
            frame_path=repo / "work" / "frames" / "smoke-live.png",
            prompt="replace actor_a with jett",
            state_path=repo / "work" / "live_state" / "smoke-live.json",
            rendered_output_path=repo / "output" / "rendered" / "smoke-live.mp4",
        ),
        chatgpt_page=chatgpt_page,
        runninghub_page=runninghub_page,
        chatgpt_adapter=ChatGptPageAdapter(start_url="https://chatgpt.com/"),
        runninghub_adapter=RunningHubPageAdapter(workflow_url="https://example.com/workflow"),
    )
    print(result)
    context.close()
'@ | uv run --with playwright python -
```

Expected: the clip reaches `done`, the live state records the final task ID, and `output/rendered/smoke-live.mp4` exists with non-zero size.

**Step 3: Verify resume after interruption**

Run the same smoke flow again after manually stopping once between submission and download.

Expected:

- the existing `runninghub_task_id` is reused
- the workflow is not resubmitted
- polling resumes and finishes download

**Step 4: Commit**

```bash
git add scripts/browser_video_remix/browser_executor.py scripts/browser_video_remix/live_runner.py scripts/browser_video_remix/runninghub_page.py tests/test_browser_video_remix_live_runner.py tests/test_browser_video_remix_runninghub_adapter.py tests/test_browser_video_remix_runninghub_page.py docs/browser-video-remix-smoke-test.md
git commit -m "feat: complete runninghub live browser flow"
```
