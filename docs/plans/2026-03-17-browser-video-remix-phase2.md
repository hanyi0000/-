# Browser Video Remix Phase 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the current browser video remix foundation into a usable phase 2 pipeline that can prepare clips with ffmpeg, persist a disk-backed manifest, drive browser sessions through Playwright adapters, and run a one-clip dry integration flow toward ChatGPT and RunningHub.

**Architecture:** Phase 2 keeps the existing package and test structure, but separates the pipeline into three concrete layers: config plus manifest models, media preparation helpers, and browser execution adapters. The real browser pages stay behind interfaces so the workflow can be verified with mocked tests before live site selectors are introduced.

**Tech Stack:** Python 3, Playwright, ffmpeg/ffprobe, PyYAML, pytest

---

### Task 1: Expand project config for real workflow settings

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\config.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-config-example.yaml`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.config import load_project_config


def test_load_project_config_reads_browser_and_split_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "split:\n"
        "  mode: fixed_duration\n"
        "  seconds: 2\n"
        "browser:\n"
        "  profile_dir: browser/profile\n"
        "  headless: false\n"
        "runninghub:\n"
        "  workflow_url: https://example.com/workflow\n"
        "actors:\n"
        "  actor_a:\n"
        "    character: jett\n"
        "    reference_image: input/jett.png\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.split.mode == "fixed_duration"
    assert config.split.seconds == 2
    assert config.browser.profile_dir.as_posix() == "browser/profile"
    assert config.runninghub.workflow_url == "https://example.com/workflow"
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_config.py::test_load_project_config_reads_browser_and_split_settings -v`
Expected: FAIL because the loader does not yet expose `split`, `browser`, or `runninghub` settings.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class SplitConfig:
    mode: str
    seconds: int


@dataclass(frozen=True)
class BrowserConfig:
    profile_dir: Path
    headless: bool


@dataclass(frozen=True)
class RunningHubConfig:
    workflow_url: str


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    split: SplitConfig
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
git commit -m "feat: expand browser remix project config"
```

### Task 2: Persist the manifest as a disk artifact

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\manifest.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest_file.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.manifest import ClipTask, save_manifest, load_manifest


def test_save_and_load_manifest_round_trip(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    tasks = [
        ClipTask(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            frame_path=Path("work/frames/clip-0001.png"),
            width=1920,
            height=1080,
            expected_resolution="1920x1080",
            state="pending",
        )
    ]

    save_manifest(manifest_path, tasks)
    loaded = load_manifest(manifest_path)

    assert loaded[0].clip_id == "clip-0001"
    assert loaded[0].clip_path.as_posix() == "work/clips/clip-0001.mp4"
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_manifest_file.py::test_save_and_load_manifest_round_trip -v`
Expected: FAIL because manifest persistence functions do not exist.

**Step 3: Write minimal implementation**

```python
def save_manifest(path: Path, tasks: list[ClipTask]) -> None:
    payload = [
        {
            "clip_id": task.clip_id,
            "clip_path": str(task.clip_path),
            "frame_path": str(task.frame_path),
            "width": task.width,
            "height": task.height,
            "expected_resolution": task.expected_resolution,
            "state": task.state,
        }
        for task in tasks
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> list[ClipTask]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        ClipTask(
            clip_id=item["clip_id"],
            clip_path=Path(item["clip_path"]),
            frame_path=Path(item["frame_path"]),
            width=item["width"],
            height=item["height"],
            expected_resolution=item["expected_resolution"],
            state=item["state"],
        )
        for item in raw
    ]
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_manifest_file.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/manifest.py tests/test_browser_video_remix_manifest_file.py
git commit -m "feat: persist browser remix manifests"
```

### Task 3: Add ffmpeg command builders for clip splitting and frame extraction

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\media.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_media_commands.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.media import build_split_command, build_frame_command


def test_build_split_command_uses_segment_output_pattern() -> None:
    command = build_split_command(
        source_video=Path("input/source.mp4"),
        output_pattern=Path("work/clips/clip-%04d.mp4"),
        seconds=2,
    )

    assert command[:2] == ["ffmpeg", "-i"]
    assert "-f" in command
    assert "segment" in command
    assert "work/clips/clip-%04d.mp4" in command


def test_build_frame_command_targets_single_output_image() -> None:
    command = build_frame_command(
        clip_path=Path("work/clips/clip-0001.mp4"),
        frame_path=Path("work/frames/clip-0001.png"),
    )

    assert command[:2] == ["ffmpeg", "-i"]
    assert "-frames:v" in command
    assert "1" in command
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_media_commands.py -q`
Expected: FAIL because command builders do not exist.

**Step 3: Write minimal implementation**

```python
def build_split_command(source_video: Path, output_pattern: Path, seconds: int) -> list[str]:
    return [
        "ffmpeg",
        "-i",
        str(source_video),
        "-f",
        "segment",
        "-segment_time",
        str(seconds),
        str(output_pattern),
    ]


def build_frame_command(clip_path: Path, frame_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-i",
        str(clip_path),
        "-frames:v",
        "1",
        str(frame_path),
    ]
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_media.py tests/test_browser_video_remix_media_commands.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/media.py tests/test_browser_video_remix_media_commands.py
git commit -m "feat: add browser remix ffmpeg command builders"
```

### Task 4: Add a preparation phase to the runner

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\cli.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_prepare_runner.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.runner import plan_prepare_run


def test_plan_prepare_run_returns_expected_artifact_paths(tmp_path: Path) -> None:
    result = plan_prepare_run(
        project_dir=tmp_path / "projects" / "demo",
        clip_count=3,
    )

    assert result.clip_count == 3
    assert result.manifest_path.name == "manifest.json"
    assert result.frames_dir.name == "frames"
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_prepare_runner.py::test_plan_prepare_run_returns_expected_artifact_paths -v`
Expected: FAIL because the prepare planner does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class PrepareRunPlan:
    project_dir: Path
    clip_count: int
    clips_dir: Path
    frames_dir: Path
    manifest_path: Path


def plan_prepare_run(project_dir: Path, clip_count: int) -> PrepareRunPlan:
    work_dir = project_dir / "work"
    return PrepareRunPlan(
        project_dir=project_dir,
        clip_count=clip_count,
        clips_dir=work_dir / "clips",
        frames_dir=work_dir / "frames",
        manifest_path=work_dir / "manifest.json",
    )
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_runner.py tests/test_browser_video_remix_prepare_runner.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/cli.py scripts/browser_video_remix/runner.py tests/test_browser_video_remix_prepare_runner.py
git commit -m "feat: add browser remix preparation planning"
```

### Task 5: Add Playwright session bootstrap behind a small adapter

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\playwright_driver.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_playwright_driver.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.playwright_driver import BrowserLaunchRequest, build_browser_launch_options


def test_build_browser_launch_options_uses_persistent_profile() -> None:
    request = BrowserLaunchRequest(
        profile_dir=Path("browser/profile"),
        headless=False,
    )

    options = build_browser_launch_options(request)

    assert options["user_data_dir"] == "browser/profile"
    assert options["headless"] is False
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_playwright_driver.py::test_build_browser_launch_options_uses_persistent_profile -v`
Expected: FAIL because the Playwright driver module does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class BrowserLaunchRequest:
    profile_dir: Path
    headless: bool


def build_browser_launch_options(request: BrowserLaunchRequest) -> dict[str, str | bool]:
    return {
        "user_data_dir": str(request.profile_dir),
        "headless": request.headless,
    }
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_playwright_driver.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/playwright_driver.py tests/test_browser_video_remix_playwright_driver.py
git commit -m "feat: add browser remix playwright bootstrap"
```

### Task 6: Add a ChatGPT page adapter with mocked execution behavior

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_chatgpt_adapter.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.browser_executor import ChatGptReferenceRequest, build_chatgpt_reference_job


def test_build_chatgpt_reference_job_tracks_input_and_output_paths() -> None:
    job = build_chatgpt_reference_job(
        clip_id="clip-0001",
        frame_path=Path("work/frames/clip-0001.png"),
        output_path=Path("work/chatgpt_refs/clip-0001.png"),
        prompt="replace actor_a with jett",
    )

    assert job.clip_id == "clip-0001"
    assert job.output_path.as_posix() == "work/chatgpt_refs/clip-0001.png"
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_chatgpt_adapter.py::test_build_chatgpt_reference_job_tracks_input_and_output_paths -v`
Expected: FAIL because the ChatGPT job model does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class ChatGptReferenceRequest:
    clip_id: str
    frame_path: Path
    output_path: Path
    prompt: str


def build_chatgpt_reference_job(clip_id: str, frame_path: Path, output_path: Path, prompt: str) -> ChatGptReferenceRequest:
    return ChatGptReferenceRequest(
        clip_id=clip_id,
        frame_path=frame_path,
        output_path=output_path,
        prompt=prompt,
    )
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_browser_executor.py tests/test_browser_video_remix_chatgpt_adapter.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/browser_executor.py tests/test_browser_video_remix_chatgpt_adapter.py
git commit -m "feat: add browser remix chatgpt adapter model"
```

### Task 7: Add a RunningHub page adapter with task polling models

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py`

**Step 1: Write the failing test**

```python
from scripts.browser_video_remix.browser_executor import RunningHubTaskStatus, is_terminal_runninghub_state


def test_is_terminal_runninghub_state_accepts_done_and_failed() -> None:
    assert is_terminal_runninghub_state(RunningHubTaskStatus.DONE) is True
    assert is_terminal_runninghub_state(RunningHubTaskStatus.FAILED) is True
    assert is_terminal_runninghub_state(RunningHubTaskStatus.RUNNING) is False
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_runninghub_adapter.py::test_is_terminal_runninghub_state_accepts_done_and_failed -v`
Expected: FAIL because the status enum and helper do not exist.

**Step 3: Write minimal implementation**

```python
class RunningHubTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


def is_terminal_runninghub_state(status: RunningHubTaskStatus) -> bool:
    return status in {RunningHubTaskStatus.DONE, RunningHubTaskStatus.FAILED}
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_runninghub_adapter.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/browser_executor.py tests/test_browser_video_remix_runninghub_adapter.py
git commit -m "feat: add browser remix runninghub task states"
```

### Task 8: Wire one-clip end-to-end orchestration and update operator docs

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\cli.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_single_clip_flow.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.runner import build_single_clip_flow_summary


def test_build_single_clip_flow_summary_includes_manifest_and_render_target(tmp_path: Path) -> None:
    summary = build_single_clip_flow_summary(
        project_dir=tmp_path / "projects" / "demo",
        clip_id="clip-0001",
    )

    assert summary["clip_id"] == "clip-0001"
    assert summary["manifest_path"].endswith("manifest.json")
    assert summary["render_output"].endswith("clip-0001.mp4")
```

**Step 2: Run test to verify it fails**

Run: `& 'F:\anconda3\python.exe' -m pytest tests/test_browser_video_remix_single_clip_flow.py::test_build_single_clip_flow_summary_includes_manifest_and_render_target -v`
Expected: FAIL because the orchestration summary helper does not exist.

**Step 3: Write minimal implementation**

```python
def build_single_clip_flow_summary(project_dir: Path, clip_id: str) -> dict[str, str]:
    return {
        "clip_id": clip_id,
        "manifest_path": str(project_dir / "work" / "manifest.json"),
        "render_output": str(project_dir / "output" / "rendered" / f"{clip_id}.mp4"),
    }
```

**Step 4: Run test to verify it passes**

Run: `& 'F:\anconda3\python.exe' -m pytest -q`
Expected: PASS with the full suite still green.

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/cli.py scripts/browser_video_remix/runner.py docs/browser-video-remix-smoke-test.md tests/test_browser_video_remix_single_clip_flow.py
git commit -m "feat: add browser remix single-clip flow scaffolding"
```
