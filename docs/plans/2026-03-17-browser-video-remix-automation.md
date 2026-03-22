# Browser Video Remix Automation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a browser-first automation tool that splits one raw video into clips, generates ChatGPT reference images, submits clip jobs to RunningHub, resumes safely after failures, and outputs validated rendered clips ready for Jianying merge.

**Architecture:** The implementation uses a local Python orchestrator with a project config, a task manifest, ffmpeg-based media preparation, and a Playwright browser executor. All clip work is checkpointed on disk so the system can validate outputs, isolate failures, and resume partially completed batches without rerunning finished clips.

**Tech Stack:** Python 3, Playwright, ffmpeg/ffprobe, PyYAML, pytest

---

### Task 1: Create the project skeleton and CLI entrypoint

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\__init__.py`
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\cli.py`
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\paths.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_cli.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.cli import build_project_paths


def test_build_project_paths_returns_expected_structure(tmp_path: Path):
    result = build_project_paths(tmp_path / "projects" / "demo")
    assert result.project_dir == tmp_path / "projects" / "demo"
    assert result.input_dir.name == "input"
    assert result.work_clips_dir.name == "clips"
    assert result.output_rendered_dir.name == "rendered"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_cli.py::test_build_project_paths_returns_expected_structure -v`
Expected: FAIL with import or attribute errors because the package does not exist yet.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    project_dir: Path
    input_dir: Path
    work_dir: Path
    work_clips_dir: Path
    work_frames_dir: Path
    work_chatgpt_refs_dir: Path
    output_dir: Path
    output_rendered_dir: Path
    output_failed_dir: Path
    logs_dir: Path


def build_project_paths(project_dir: Path) -> ProjectPaths:
    work_dir = project_dir / "work"
    output_dir = project_dir / "output"
    return ProjectPaths(
        project_dir=project_dir,
        input_dir=project_dir / "input",
        work_dir=work_dir,
        work_clips_dir=work_dir / "clips",
        work_frames_dir=work_dir / "frames",
        work_chatgpt_refs_dir=work_dir / "chatgpt_refs",
        output_dir=output_dir,
        output_rendered_dir=output_dir / "rendered",
        output_failed_dir=output_dir / "failed",
        logs_dir=project_dir / "logs",
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_cli.py::test_build_project_paths_returns_expected_structure -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_cli.py scripts/browser_video_remix/__init__.py scripts/browser_video_remix/cli.py scripts/browser_video_remix/paths.py
git commit -m "feat: scaffold browser video remix cli"
```

### Task 2: Add project config loading and validation

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\config.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.config import load_project_config


def test_load_project_config_reads_actor_mapping(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "actors:\n"
        "  actor_a:\n"
        "    character: jett\n"
        "    reference_image: input/jett.png\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.source_video.as_posix() == "input/source.mp4"
    assert config.actors["actor_a"].character == "jett"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_config.py::test_load_project_config_reads_actor_mapping -v`
Expected: FAIL because the config loader does not exist.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ActorConfig:
    character: str
    reference_image: Path


@dataclass(frozen=True)
class ProjectConfig:
    source_video: Path
    actors: dict[str, ActorConfig]


def load_project_config(config_path: Path) -> ProjectConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    actors = {
        name: ActorConfig(
            character=value["character"],
            reference_image=Path(value["reference_image"]),
        )
        for name, value in raw["actors"].items()
    }
    return ProjectConfig(source_video=Path(raw["source_video"]), actors=actors)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_config.py::test_load_project_config_reads_actor_mapping -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_config.py scripts/browser_video_remix/config.py
git commit -m "feat: add browser remix project config loader"
```

### Task 3: Implement clip metadata and manifest models

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\manifest.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_manifest.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.manifest import build_clip_task


def test_build_clip_task_sets_initial_state():
    task = build_clip_task(
        clip_id="clip-0001",
        clip_path=Path("work/clips/clip-0001.mp4"),
        frame_path=Path("work/frames/clip-0001.png"),
        width=1920,
        height=1080,
    )
    assert task.state == "pending"
    assert task.expected_resolution == "1920x1080"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_manifest.py::test_build_clip_task_sets_initial_state -v`
Expected: FAIL because the manifest module does not exist.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClipTask:
    clip_id: str
    clip_path: Path
    frame_path: Path
    width: int
    height: int
    expected_resolution: str
    state: str


def build_clip_task(clip_id: str, clip_path: Path, frame_path: Path, width: int, height: int) -> ClipTask:
    return ClipTask(
        clip_id=clip_id,
        clip_path=clip_path,
        frame_path=frame_path,
        width=width,
        height=height,
        expected_resolution=f"{width}x{height}",
        state="pending",
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_manifest.py::test_build_clip_task_sets_initial_state -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_manifest.py scripts/browser_video_remix/manifest.py
git commit -m "feat: add browser remix manifest model"
```

### Task 4: Implement persistent state transitions for clip jobs

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\state_store.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_state_store.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.state_store import FileStateStore


def test_state_store_persists_clip_state(tmp_path: Path):
    store = FileStateStore(tmp_path / "tasks.json")
    store.update("clip-0001", state="chatgpt_complete")
    reloaded = FileStateStore(tmp_path / "tasks.json")
    assert reloaded.get("clip-0001")["state"] == "chatgpt_complete"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_state_store.py::test_state_store_persists_clip_state -v`
Expected: FAIL because the state store does not exist.

**Step 3: Write minimal implementation**

```python
import json
from pathlib import Path


class FileStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))
        else:
            self._data = {}

    def update(self, clip_id: str, **values: str) -> None:
        self._data.setdefault(clip_id, {}).update(values)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, clip_id: str) -> dict[str, str]:
        return self._data[clip_id]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_state_store.py::test_state_store_persists_clip_state -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_state_store.py scripts/browser_video_remix/state_store.py
git commit -m "feat: add browser remix state persistence"
```

### Task 5: Add resolution rule evaluation

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\resolution.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_resolution.py`

**Step 1: Write the failing test**

```python
from scripts.browser_video_remix.resolution import choose_resize_action


def test_choose_resize_action_returns_none_for_matching_ratio():
    action = choose_resize_action(
        clip_width=1920,
        clip_height=1080,
        ref_width=1024,
        ref_height=576,
        target_width=1920,
        target_height=1080,
    )
    assert action == "none"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_resolution.py::test_choose_resize_action_returns_none_for_matching_ratio -v`
Expected: FAIL because the resolution module does not exist.

**Step 3: Write minimal implementation**

```python
def choose_resize_action(
    clip_width: int,
    clip_height: int,
    ref_width: int,
    ref_height: int,
    target_width: int,
    target_height: int,
) -> str:
    clip_ratio = clip_width / clip_height
    ref_ratio = ref_width / ref_height
    target_ratio = target_width / target_height
    if round(clip_ratio, 4) == round(ref_ratio, 4) == round(target_ratio, 4):
        return "none"
    return "pad"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_resolution.py::test_choose_resize_action_returns_none_for_matching_ratio -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_resolution.py scripts/browser_video_remix/resolution.py
git commit -m "feat: add browser remix resolution rules"
```

### Task 6: Add ffprobe metadata extraction and clip preparation helpers

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\media.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_media.py`

**Step 1: Write the failing test**

```python
from scripts.browser_video_remix.media import parse_ffprobe_video_stream


def test_parse_ffprobe_video_stream_reads_dimensions():
    stream = {"width": 1920, "height": 1080, "r_frame_rate": "24/1", "duration": "3.2"}
    metadata = parse_ffprobe_video_stream(stream)
    assert metadata.width == 1920
    assert metadata.height == 1080
    assert metadata.frame_rate == 24.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_media.py::test_parse_ffprobe_video_stream_reads_dimensions -v`
Expected: FAIL because the media module does not exist.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    frame_rate: float
    duration: float


def parse_ffprobe_video_stream(stream: dict[str, str | int]) -> VideoMetadata:
    numerator, denominator = str(stream["r_frame_rate"]).split("/")
    return VideoMetadata(
        width=int(stream["width"]),
        height=int(stream["height"]),
        frame_rate=float(numerator) / float(denominator),
        duration=float(stream["duration"]),
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_media.py::test_parse_ffprobe_video_stream_reads_dimensions -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_media.py scripts/browser_video_remix/media.py
git commit -m "feat: add browser remix media metadata helpers"
```

### Task 7: Add ChatGPT prompt rendering for multi-actor replacement

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\prompts.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_prompts.py`

**Step 1: Write the failing test**

```python
from scripts.browser_video_remix.prompts import render_chatgpt_prompt


def test_render_chatgpt_prompt_includes_all_actor_mappings():
    prompt = render_chatgpt_prompt(
        scene_description="cinematic indoor dialogue scene",
        mappings={"actor_a": "jett", "actor_b": "sage"},
    )
    assert "actor_a" in prompt
    assert "jett" in prompt
    assert "actor_b" in prompt
    assert "sage" in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_prompts.py::test_render_chatgpt_prompt_includes_all_actor_mappings -v`
Expected: FAIL because the prompt helper does not exist.

**Step 3: Write minimal implementation**

```python
def render_chatgpt_prompt(scene_description: str, mappings: dict[str, str]) -> str:
    lines = [
        "Replace the people in this frame while preserving composition, lighting, and camera angle.",
        f"Scene: {scene_description}",
    ]
    for actor_name, character_name in mappings.items():
        lines.append(f"Replace {actor_name} with {character_name}.")
    return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_prompts.py::test_render_chatgpt_prompt_includes_all_actor_mappings -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_prompts.py scripts/browser_video_remix/prompts.py
git commit -m "feat: add browser remix prompt rendering"
```

### Task 8: Add a browser abstraction for clip-level execution

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\browser_executor.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_browser_executor.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.browser_executor import ClipExecutionRequest, build_runninghub_payload


def test_build_runninghub_payload_uses_clip_resolution():
    payload = build_runninghub_payload(
        ClipExecutionRequest(
            clip_id="clip-0001",
            clip_path=Path("work/clips/clip-0001.mp4"),
            reference_image_path=Path("work/chatgpt_refs/clip-0001.png"),
            prompt="replace actor_a with jett",
            width=1920,
            height=1080,
        )
    )
    assert payload["resolution"] == "1920x1080"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_browser_executor.py::test_build_runninghub_payload_uses_clip_resolution -v`
Expected: FAIL because the browser executor does not exist.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClipExecutionRequest:
    clip_id: str
    clip_path: Path
    reference_image_path: Path
    prompt: str
    width: int
    height: int


def build_runninghub_payload(request: ClipExecutionRequest) -> dict[str, str]:
    return {
        "clip_id": request.clip_id,
        "video_path": str(request.clip_path),
        "reference_image_path": str(request.reference_image_path),
        "prompt": request.prompt,
        "resolution": f"{request.width}x{request.height}",
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_browser_executor.py::test_build_runninghub_payload_uses_clip_resolution -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_browser_executor.py scripts/browser_video_remix/browser_executor.py
git commit -m "feat: add browser remix execution payload builder"
```

### Task 9: Implement resume filtering for partially completed batches

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\resume.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_resume.py`

**Step 1: Write the failing test**

```python
from scripts.browser_video_remix.resume import filter_pending_clip_ids


def test_filter_pending_clip_ids_skips_completed_jobs():
    clip_ids = ["clip-0001", "clip-0002", "clip-0003"]
    state_map = {
        "clip-0001": {"state": "done"},
        "clip-0002": {"state": "runninghub_complete"},
        "clip-0003": {"state": "submit_failed"},
    }
    assert filter_pending_clip_ids(clip_ids, state_map) == ["clip-0003"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_resume.py::test_filter_pending_clip_ids_skips_completed_jobs -v`
Expected: FAIL because the resume helper does not exist.

**Step 3: Write minimal implementation**

```python
def filter_pending_clip_ids(clip_ids: list[str], state_map: dict[str, dict[str, str]]) -> list[str]:
    finished_states = {"done", "runninghub_complete"}
    return [clip_id for clip_id in clip_ids if state_map.get(clip_id, {}).get("state") not in finished_states]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_resume.py::test_filter_pending_clip_ids_skips_completed_jobs -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_resume.py scripts/browser_video_remix/resume.py
git commit -m "feat: add browser remix resume filtering"
```

### Task 10: Implement output validation and batch report generation

**Files:**
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\validation.py`
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\reporting.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_validation.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.validation import validate_rendered_clip


def test_validate_rendered_clip_reports_missing_file(tmp_path: Path):
    result = validate_rendered_clip(
        clip_id="clip-0001",
        rendered_path=tmp_path / "missing.mp4",
        expected_width=1920,
        expected_height=1080,
    )
    assert result.is_valid is False
    assert result.reason == "missing_file"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_validation.py::test_validate_rendered_clip_reports_missing_file -v`
Expected: FAIL because the validation module does not exist.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    clip_id: str
    is_valid: bool
    reason: str


def validate_rendered_clip(clip_id: str, rendered_path: Path, expected_width: int, expected_height: int) -> ValidationResult:
    if not rendered_path.exists():
        return ValidationResult(clip_id=clip_id, is_valid=False, reason="missing_file")
    return ValidationResult(clip_id=clip_id, is_valid=True, reason="ok")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_validation.py::test_validate_rendered_clip_reports_missing_file -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_validation.py scripts/browser_video_remix/validation.py scripts/browser_video_remix/reporting.py
git commit -m "feat: add browser remix validation and reporting"
```

### Task 11: Wire the end-to-end batch runner with dry-run mode

**Files:**
- Modify: `D:\edge\新建文件夹\scripts\browser_video_remix\cli.py`
- Create: `D:\edge\新建文件夹\scripts\browser_video_remix\runner.py`
- Create: `D:\edge\新建文件夹\tests\test_browser_video_remix_runner.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.browser_video_remix.runner import plan_batch_run


def test_plan_batch_run_returns_clip_count(tmp_path: Path):
    result = plan_batch_run(
        project_dir=tmp_path / "projects" / "demo",
        manifest_entries=["clip-0001", "clip-0002"],
        dry_run=True,
    )
    assert result.clip_count == 2
    assert result.dry_run is True
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_video_remix_runner.py::test_plan_batch_run_returns_clip_count -v`
Expected: FAIL because the runner does not exist.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatchRunPlan:
    project_dir: Path
    clip_count: int
    dry_run: bool


def plan_batch_run(project_dir: Path, manifest_entries: list[str], dry_run: bool) -> BatchRunPlan:
    return BatchRunPlan(project_dir=project_dir, clip_count=len(manifest_entries), dry_run=dry_run)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_browser_video_remix_runner.py::test_plan_batch_run_returns_clip_count -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_browser_video_remix_runner.py scripts/browser_video_remix/cli.py scripts/browser_video_remix/runner.py
git commit -m "feat: add browser remix batch runner"
```

### Task 12: Add a real-session smoke test checklist and operator docs

**Files:**
- Create: `D:\edge\新建文件夹\docs\browser-video-remix-smoke-test.md`
- Modify: `D:\edge\新建文件夹\docs\plans\2026-03-17-browser-video-remix-automation-design.md`

**Step 1: Write the failing test**

No automated test is needed for this documentation task. Instead, define a manual checklist that must be executed before claiming the browser integration is usable.

**Step 2: Run test to verify it fails**

Not applicable. The failure condition is the absence of a documented manual smoke test.

**Step 3: Write minimal implementation**

Document:

- required local dependencies
- how to prepare a project config
- how to launch the browser with a persistent profile
- how to run in dry-run mode
- how to run one clip end-to-end
- how to verify ChatGPT output image, RunningHub submission, download path, and resume behavior

**Step 4: Run test to verify it passes**

Manual verification: read the checklist and confirm it covers the full operator flow without hidden steps.

**Step 5: Commit**

```bash
git add docs/browser-video-remix-smoke-test.md docs/plans/2026-03-17-browser-video-remix-automation-design.md
git commit -m "docs: add browser remix smoke test guide"
```
