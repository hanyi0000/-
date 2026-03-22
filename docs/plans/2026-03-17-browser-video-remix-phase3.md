# Browser Video Remix Phase 3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a real single-clip browser automation flow that can drive ChatGPT and RunningHub with a dedicated browser profile, persist live state to disk, pause for operator intervention, and resume safely.

**Architecture:** Phase 3 adds three concrete layers on top of the current scaffold: expanded live-run config, disk-backed live state, and real browser page adapters for ChatGPT and RunningHub. A new live runner coordinates one clip end to end while treating login expiry, captcha, and selector drift as explicit pause states rather than generic failures.

**Tech Stack:** Python 3, Playwright sync API, PyYAML, pytest

---

### Task 1: Expand config for live browser session settings

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\config.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-config-example.yaml`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.config import load_project_config


def test_load_project_config_reads_live_browser_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "chatgpt:\n"
        "  start_url: https://chatgpt.com/g/test\n"
        "  prompt_timeout_ms: 90000\n"
        "browser:\n"
        "  profile_dir: browser/profile\n"
        "  downloads_dir: work/downloads\n"
        "  default_timeout_ms: 15000\n"
        "  headless: false\n"
        "runninghub:\n"
        "  workflow_url: https://example.com/workflow\n"
        "  poll_interval_seconds: 5\n"
        "actors:\n"
        "  actor_a:\n"
        "    character: jett\n"
        "    reference_image: input/jett.png\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.chatgpt.start_url == "https://chatgpt.com/g/test"
    assert config.chatgpt.prompt_timeout_ms == 90000
    assert config.browser.downloads_dir.as_posix() == "work/downloads"
    assert config.browser.default_timeout_ms == 15000
    assert config.runninghub.poll_interval_seconds == 5
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_config.py::test_load_project_config_reads_live_browser_settings -v`
Expected: FAIL because the config loader does not yet expose `chatgpt`, browser download settings, or RunningHub poll settings.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class ChatGptConfig:
    start_url: str
    prompt_timeout_ms: int


@dataclass(frozen=True)
class BrowserConfig:
    profile_dir: Path
    downloads_dir: Path
    default_timeout_ms: int
    headless: bool


@dataclass(frozen=True)
class RunningHubConfig:
    workflow_url: str
    poll_interval_seconds: int


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    split: SplitConfig
    chatgpt: ChatGptConfig
    browser: BrowserConfig
    runninghub: RunningHubConfig
    actors: dict[str, ActorConfig]
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_config.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/browser-video-remix-config-example.yaml scripts/browser_video_remix/config.py tests/test_browser_video_remix_config.py
git commit -m "feat: expand live browser remix config"
```

### Task 2: Add disk-backed live state for pause and resume

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_state.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_state.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.live_state import (
    LiveClipState,
    PauseReason,
    load_live_state,
    save_live_state,
)


def test_save_and_load_live_state_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "clip-0001.json"
    state = LiveClipState(
        clip_id="clip-0001",
        step="reference_saved",
        reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
        rendered_output_path=None,
        runninghub_task_id=None,
        pause_reason=PauseReason.LOGIN_REQUIRED,
        last_error=None,
        last_screenshot_path=Path("work/screenshots/clip-0001-login.png"),
    )

    save_live_state(state_path, state)
    loaded = load_live_state(state_path)

    assert loaded.step == "reference_saved"
    assert loaded.pause_reason == PauseReason.LOGIN_REQUIRED
    assert loaded.reference_image_path.as_posix() == "work/chatgpt_refs/clip-0001.png"
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_live_state.py::test_save_and_load_live_state_round_trip -v`
Expected: FAIL because the live state module does not exist.

**Step 3: Write minimal implementation**

```python
class PauseReason(str, Enum):
    LOGIN_REQUIRED = "login_required"
    CAPTCHA_REQUIRED = "captcha_required"
    SELECTOR_MISSING = "selector_missing"
    PAGE_CHANGED = "page_changed"
    MANUAL_CONFIRMATION_REQUIRED = "manual_confirmation_required"


@dataclass(frozen=True)
class LiveClipState:
    clip_id: str
    step: str
    reference_image_path: Path | None
    rendered_output_path: Path | None
    runninghub_task_id: str | None
    pause_reason: PauseReason | None
    last_error: str | None
    last_screenshot_path: Path | None
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_live_state.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/live_state.py tests/test_browser_video_remix_live_state.py
git commit -m "feat: add browser remix live state persistence"
```

### Task 3: Extend the Playwright driver for persistent contexts and downloads

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\playwright_driver.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_playwright_driver.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.playwright_driver import (
    PersistentContextRequest,
    build_persistent_context_options,
)


def test_build_persistent_context_options_sets_downloads_and_timeout() -> None:
    request = PersistentContextRequest(
        profile_dir=Path("browser/profile"),
        downloads_dir=Path("work/downloads"),
        default_timeout_ms=15000,
        headless=False,
    )

    options = build_persistent_context_options(request)

    assert options["user_data_dir"] == "browser/profile"
    assert options["downloads_path"] == "work/downloads"
    assert options["accept_downloads"] is True
    assert options["default_timeout_ms"] == 15000
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_playwright_driver.py::test_build_persistent_context_options_sets_downloads_and_timeout -v`
Expected: FAIL because the driver does not yet model downloads or default timeout.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class PersistentContextRequest:
    profile_dir: Path
    downloads_dir: Path
    default_timeout_ms: int
    headless: bool


def build_persistent_context_options(request: PersistentContextRequest) -> dict[str, str | bool | int]:
    return {
        "user_data_dir": request.profile_dir.as_posix(),
        "downloads_path": request.downloads_dir.as_posix(),
        "accept_downloads": True,
        "default_timeout_ms": request.default_timeout_ms,
        "headless": request.headless,
    }
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_playwright_driver.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/playwright_driver.py tests/test_browser_video_remix_playwright_driver.py
git commit -m "feat: extend browser remix playwright driver"
```

### Task 4: Add a real ChatGPT page adapter with pause classification

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\chatgpt_page.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_chatgpt_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_chatgpt_page.py::test_chatgpt_adapter_pauses_when_login_is_required -v`
Expected: FAIL because the live ChatGPT page adapter does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class AdapterResult:
    status: str
    output_path: Path | None
    pause_reason: PauseReason | None


class ChatGptPageAdapter:
    def __init__(self, start_url: str) -> None:
        self.start_url = start_url

    def submit_reference_generation(self, page: object, request: ChatGptReferenceRequest) -> AdapterResult:
        if getattr(page, "login_required", False):
            return AdapterResult(
                status="paused",
                output_path=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return AdapterResult(
            status="completed",
            output_path=request.output_path,
            pause_reason=None,
        )
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_chatgpt_page.py tests/test_browser_video_remix_chatgpt_adapter.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/browser_executor.py scripts/browser_video_remix/chatgpt_page.py tests/test_browser_video_remix_chatgpt_page.py
git commit -m "feat: add live browser remix chatgpt adapter"
```

### Task 5: Add a real RunningHub page adapter with submit and poll outcomes

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.browser_executor import ClipExecutionRequest
from scripts.browser_video_remix.live_state import PauseReason
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


class FakeRunningHubPage:
    def __init__(self, login_required: bool = False, task_id: str = "task-123") -> None:
        self.login_required = login_required
        self.task_id = task_id


def test_runninghub_adapter_returns_task_id_for_submitted_job() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://example.com/workflow")
    result = adapter.submit_render_job(
        page=FakeRunningHubPage(),
        request=ClipExecutionRequest(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
            width=1920,
            height=1080,
        ),
    )

    assert result.status == "submitted"
    assert result.task_id == "task-123"
    assert result.pause_reason is None
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_runninghub_page.py::test_runninghub_adapter_returns_task_id_for_submitted_job -v`
Expected: FAIL because the RunningHub page adapter does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class RunningHubSubmitResult:
    status: str
    task_id: str | None
    pause_reason: PauseReason | None


class RunningHubPageAdapter:
    def __init__(self, workflow_url: str) -> None:
        self.workflow_url = workflow_url

    def submit_render_job(self, page: object, request: ClipExecutionRequest) -> RunningHubSubmitResult:
        if getattr(page, "login_required", False):
            return RunningHubSubmitResult(
                status="paused",
                task_id=None,
                pause_reason=PauseReason.LOGIN_REQUIRED,
            )
        return RunningHubSubmitResult(
            status="submitted",
            task_id=getattr(page, "task_id", None),
            pause_reason=None,
        )
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_runninghub_page.py tests/test_browser_video_remix_runninghub_adapter.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/browser_executor.py scripts/browser_video_remix/runninghub_page.py tests/test_browser_video_remix_runninghub_page.py
git commit -m "feat: add live browser remix runninghub adapter"
```

### Task 6: Add a single-clip live runner with resume-aware sequencing

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_runner.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runner.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow


class FakeChatGptAdapter:
    def submit_reference_generation(self, page: object, request: object) -> object:
        return type("Result", (), {"status": "completed", "output_path": Path("work/chatgpt_refs/clip-0001.png"), "pause_reason": None})()


class FakeRunningHubAdapter:
    def submit_render_job(self, page: object, request: object) -> object:
        return type("Result", (), {"status": "submitted", "task_id": "task-123", "pause_reason": None})()


def test_run_single_clip_live_flow_returns_state_path_and_task_id(tmp_path: Path) -> None:
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
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_live_runner.py::test_run_single_clip_live_flow_returns_state_path_and_task_id -v`
Expected: FAIL because the live runner does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class LiveClipRequest:
    clip_id: str
    clip_path: Path
    frame_path: Path
    prompt: str
    state_path: Path
    rendered_output_path: Path


def run_single_clip_live_flow(
    request: LiveClipRequest,
    chatgpt_page: object,
    runninghub_page: object,
    chatgpt_adapter: object,
    runninghub_adapter: object,
) -> dict[str, str]:
    reference_result = chatgpt_adapter.submit_reference_generation(chatgpt_page, request)
    runninghub_result = runninghub_adapter.submit_render_job(runninghub_page, request)
    return {
        "clip_id": request.clip_id,
        "task_id": str(runninghub_result.task_id),
        "state_path": str(request.state_path),
        "reference_image_path": str(reference_result.output_path),
    }
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_live_runner.py tests/test_browser_video_remix_runner.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/live_runner.py scripts/browser_video_remix/runner.py tests/test_browser_video_remix_live_runner.py
git commit -m "feat: add browser remix live single-clip runner"
```

### Task 7: Wire CLI live-run request building and update operator docs

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\cli.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_cli.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.cli import build_live_run_request


def test_build_live_run_request_points_to_state_and_downloads(tmp_path: Path) -> None:
    request = build_live_run_request(
        project_dir=tmp_path / "projects" / "demo",
        clip_id="clip-0001",
    )

    assert request.clip_id == "clip-0001"
    assert request.state_path.name == "clip-0001.json"
    assert request.downloads_dir.name == "downloads"
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_live_cli.py::test_build_live_run_request_points_to_state_and_downloads -v`
Expected: FAIL because the CLI layer does not yet expose a live-run request helper.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class LiveRunRequest:
    clip_id: str
    state_path: Path
    downloads_dir: Path
    rendered_output_path: Path


def build_live_run_request(project_dir: Path, clip_id: str) -> LiveRunRequest:
    paths = _build_project_paths(project_dir)
    return LiveRunRequest(
        clip_id=clip_id,
        state_path=paths.work_dir / "live_state" / f"{clip_id}.json",
        downloads_dir=paths.work_dir / "downloads",
        rendered_output_path=paths.output_rendered_dir / f"{clip_id}.mp4",
    )
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest -q`
Expected: PASS with the full suite still green.

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/cli.py docs/browser-video-remix-smoke-test.md tests/test_browser_video_remix_live_cli.py
git commit -m "feat: wire browser remix live clip requests"
```
