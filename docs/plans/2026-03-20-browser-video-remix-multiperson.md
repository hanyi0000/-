# Browser Video Remix Multiperson Automation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the current browser remix pipeline into a multiperson, shot-based automation flow with local shot segmentation, fixed identity mapping, per-person reference generation, workflow binding for the target Wan Animate RunningHub workflow, and replacement quality audits with up to three automatic retries.

**Architecture:** Keep the existing repository structure and evolve it incrementally. Preserve `clip_id` as the stable shot identifier, upgrade the config and manifest layers first, then add local vision helpers for shot detection and face/keyframe selection, then introduce workflow introspection and multiperson binding, and finally wire quality audits plus retry orchestration into the live runner. All new browser drift remains isolated to adapters, while state, retry, and audit logic remain local and testable.

**Tech Stack:** Python 3, pytest, PyYAML, Playwright sync API, ffmpeg/ffprobe, PySceneDetect, OpenCV contrib models

---

### Task 1: Expand project config for multiperson identities, role strategies, audits, and retries

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\config.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_config.py`

**Step 1: Write the failing tests**

Add a new config test that exercises the new project sections:

```python
def test_load_project_config_reads_multiperson_identity_and_retry_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "source_video: input/source.mp4\n"
        "segmentation:\n"
        "  mode: content\n"
        "  min_seconds: 1.0\n"
        "  threshold: 28.5\n"
        "source_identities:\n"
        "  actor_a:\n"
        "    sample_images:\n"
        "      - assets/source_people/actor_a_01.png\n"
        "target_roles:\n"
        "  jett:\n"
        "    strategy: hybrid\n"
        "    prompt: valorant jett\n"
        "    reference_images:\n"
        "      - assets/target_roles/jett/ref_01.png\n"
        "    lora:\n"
        "      name: jett_v1\n"
        "      weight: 0.8\n"
        "identity_mapping:\n"
        "  actor_a: jett\n"
        "quality_audit:\n"
        "  max_background_delta: 0.18\n"
        "retry:\n"
        "  max_attempts: 3\n",
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.segmentation.mode == "content"
    assert config.source_identities["actor_a"].sample_images[0].as_posix().endswith("actor_a_01.png")
    assert config.target_roles["jett"].strategy == "hybrid"
    assert config.target_roles["jett"].lora.name == "jett_v1"
    assert config.identity_mapping["actor_a"] == "jett"
    assert config.retry.max_attempts == 3
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with pyyaml pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_config.py -q`

Expected: FAIL because `ProjectConfig` does not yet expose `segmentation`, `source_identities`, `target_roles`, `identity_mapping`, `quality_audit`, or `retry`.

**Step 3: Write the minimal implementation**

Add new config dataclasses while keeping the current fields working:

```python
@dataclass(frozen=True)
class SegmentationConfig:
    mode: str
    min_seconds: float
    threshold: float


@dataclass(frozen=True)
class SourceIdentityConfig:
    sample_images: list[Path]


@dataclass(frozen=True)
class LoraConfig:
    name: str
    weight: float


@dataclass(frozen=True)
class TargetRoleConfig:
    strategy: str
    prompt: str
    reference_images: list[Path]
    lora: LoraConfig | None


@dataclass(frozen=True)
class QualityAuditConfig:
    max_background_delta: float


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int
```

Parse them in `load_project_config()` with sensible defaults:

```python
segmentation = raw_config.get("segmentation", {})
quality_audit = raw_config.get("quality_audit", {})
retry = raw_config.get("retry", {})
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with pyyaml pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_config.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/config.py tests/test_browser_video_remix_config.py
git commit -m "feat: add multiperson remix project config"
```

### Task 2: Expand project paths and manifest for shot-based multiperson state

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\paths.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\manifest.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest_file.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_paths.py`

**Step 1: Write the failing tests**

Add path coverage for new working directories:

```python
def test_build_project_paths_includes_multiperson_work_dirs(tmp_path: Path) -> None:
    paths = build_project_paths(tmp_path)

    assert paths.work_shots_dir == tmp_path / "work" / "shots"
    assert paths.work_keyframes_dir == tmp_path / "work" / "keyframes"
    assert paths.work_workflow_bindings_dir == tmp_path / "work" / "workflow_bindings"
    assert paths.logs_notifications_dir == tmp_path / "logs" / "notifications"
```

Add manifest coverage for shot metadata and per-person reference tracking:

```python
def test_build_clip_task_sets_shot_metadata_and_retry_defaults() -> None:
    task = build_clip_task(
        clip_id="clip-0001",
        clip_path=Path("work/shots/clip-0001.mp4"),
        frame_path=Path("work/keyframes/clip-0001_actor_a.png"),
        width=1920,
        height=1080,
        start_ms=0,
        end_ms=2400,
    )

    assert task.start_ms == 0
    assert task.end_ms == 2400
    assert task.retry_count == 0
    assert task.person_reference_images == {}
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest_file.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_paths.py -q`

Expected: FAIL because the paths and manifest models do not yet include the new directories or fields.

**Step 3: Write the minimal implementation**

Extend `ProjectPaths`:

```python
@dataclass(frozen=True)
class ProjectPaths:
    ...
    work_shots_dir: Path
    work_face_detections_dir: Path
    work_keyframes_dir: Path
    work_workflow_bindings_dir: Path
    work_quality_reports_dir: Path
    logs_notifications_dir: Path
```

Extend `ClipTask` without changing the stable `clip_id`:

```python
@dataclass(frozen=True)
class ClipTask:
    clip_id: str
    clip_path: Path
    frame_path: Path
    width: int
    height: int
    expected_resolution: str
    state: str
    start_ms: int
    end_ms: int
    retry_count: int
    person_reference_images: dict[str, str]
```

Update `save_manifest()` and `load_manifest()` accordingly.

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_manifest_file.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_paths.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/paths.py scripts/browser_video_remix/manifest.py tests/test_browser_video_remix_manifest.py tests/test_browser_video_remix_manifest_file.py tests/test_browser_video_remix_paths.py
git commit -m "feat: add shot and multiperson project paths"
```

### Task 3: Add local shot segmentation with PySceneDetect and manifest generation

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\shot_splitter.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_prepare_runner.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_shot_splitter.py`

**Step 1: Write the failing tests**

Create a shot splitter test using a fake detector:

```python
def test_build_shot_tasks_from_detected_boundaries(tmp_path: Path) -> None:
    source_video = tmp_path / "input" / "source.mp4"
    source_video.parent.mkdir(parents=True, exist_ok=True)
    source_video.write_bytes(b"video")

    tasks = build_shot_tasks(
        source_video=source_video,
        boundaries=[(0, 2400), (2400, 5100)],
        shots_dir=tmp_path / "work" / "shots",
    )

    assert [task.clip_id for task in tasks] == ["clip-0001", "clip-0002"]
    assert tasks[0].clip_path.as_posix().endswith("clip-0001.mp4")
    assert tasks[1].start_ms == 2400
```

Add a planning test to `runner.py` that expects shot-based outputs under `work/shots`.

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with scenedetect pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_prepare_runner.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_shot_splitter.py -q`

Expected: FAIL because there is no shot splitter module and the runner still assumes the old clip preparation flow.

**Step 3: Write the minimal implementation**

Create a helper that separates pure planning from actual scene detection:

```python
def build_shot_tasks(
    source_video: Path,
    boundaries: list[tuple[int, int]],
    shots_dir: Path,
) -> list[ClipTask]:
    tasks: list[ClipTask] = []
    for index, (start_ms, end_ms) in enumerate(boundaries, start=1):
        clip_id = f"clip-{index:04d}"
        tasks.append(
            build_clip_task(
                clip_id=clip_id,
                clip_path=shots_dir / f"{clip_id}.mp4",
                frame_path=Path(""),
                width=0,
                height=0,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )
    return tasks
```

Add `detect_shot_boundaries()` using PySceneDetect for live use and keep `runner.py` calling the planning helper.

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with scenedetect pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_prepare_runner.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_shot_splitter.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/shot_splitter.py scripts/browser_video_remix/runner.py tests/test_browser_video_remix_prepare_runner.py tests/test_browser_video_remix_shot_splitter.py
git commit -m "feat: add local shot segmentation planning"
```

### Task 4: Add source identity index and target role strategy resolution

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\identity_registry.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_identity_registry.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_browser_executor.py`

**Step 1: Write the failing tests**

Create a strategy-resolution test:

```python
def test_build_role_execution_plan_prefers_hybrid_when_assets_exist() -> None:
    registry = build_identity_registry(
        source_identities={"actor_a": SourceIdentityConfig(sample_images=[Path("a.png")])},
        target_roles={
            "jett": TargetRoleConfig(
                strategy="hybrid",
                prompt="valorant jett",
                reference_images=[Path("jett.png")],
                lora=LoraConfig(name="jett_v1", weight=0.8),
            )
        },
        identity_mapping={"actor_a": "jett"},
    )

    plan = registry.role_plan_for("actor_a")

    assert plan.target_role_id == "jett"
    assert plan.strategy == "hybrid"
    assert plan.lora_name == "jett_v1"
```

Also extend `browser_executor.py` tests to cover a new multiperson request model, for example `PersonReferenceRequest`.

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with pyyaml pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_identity_registry.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_browser_executor.py -q`

Expected: FAIL because the identity registry and per-person execution models do not yet exist.

**Step 3: Write the minimal implementation**

Create a small registry module:

```python
@dataclass(frozen=True)
class RoleExecutionPlan:
    source_person_id: str
    target_role_id: str
    strategy: str
    prompt: str
    reference_images: list[Path]
    lora_name: str | None
    lora_weight: float | None


class IdentityRegistry:
    def __init__(...):
        ...

    def role_plan_for(self, source_person_id: str) -> RoleExecutionPlan:
        ...
```

Extend `browser_executor.py` with the request/result models that downstream ChatGPT and RunningHub code will need.

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with pyyaml pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_identity_registry.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_browser_executor.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/identity_registry.py scripts/browser_video_remix/browser_executor.py tests/test_browser_video_remix_identity_registry.py tests/test_browser_video_remix_browser_executor.py
git commit -m "feat: add multiperson identity registry"
```

### Task 5: Add face analysis and best frontal frame selection helpers

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\face_analysis.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\keyframe_selection.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_face_analysis.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_keyframe_selection.py`

**Step 1: Write the failing tests**

Add a score-ordering test for keyframe selection:

```python
def test_choose_best_face_frame_prefers_large_sharp_frontal_face() -> None:
    candidates = [
        FaceObservation(frame_path=Path("a.png"), person_id="actor_a", score=0.42, confidence=0.70),
        FaceObservation(frame_path=Path("b.png"), person_id="actor_a", score=0.88, confidence=0.93),
        FaceObservation(frame_path=Path("c.png"), person_id="actor_a", score=0.61, confidence=0.81),
    ]

    selected = choose_best_face_frame(candidates)

    assert selected.frame_path == Path("b.png")
```

Add a registry-backed assignment test:

```python
def test_match_known_identities_returns_person_id_when_similarity_is_high() -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with numpy --with opencv-contrib-python pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_face_analysis.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_keyframe_selection.py -q`

Expected: FAIL because the local face analysis modules do not yet exist.

**Step 3: Write the minimal implementation**

Start with pure-Python models and deterministic helpers so tests stay cheap:

```python
@dataclass(frozen=True)
class FaceObservation:
    frame_path: Path
    person_id: str | None
    score: float
    confidence: float


def choose_best_face_frame(observations: list[FaceObservation]) -> FaceObservation:
    return max(observations, key=lambda item: item.score)
```

Then add a thin OpenCV-backed analyzer behind a small interface:

```python
class FaceAnalyzer:
    def detect_faces(self, frame_path: Path) -> list[FaceObservation]:
        ...
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with numpy --with opencv-contrib-python pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_face_analysis.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_keyframe_selection.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/face_analysis.py scripts/browser_video_remix/keyframe_selection.py tests/test_browser_video_remix_face_analysis.py tests/test_browser_video_remix_keyframe_selection.py
git commit -m "feat: add face analysis and keyframe selection"
```

### Task 6: Extend ChatGPT reference generation to per-person outputs

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\chatgpt_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_state.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_chatgpt_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_state.py`

**Step 1: Write the failing tests**

Add a state test for per-person references:

```python
def test_save_live_state_persists_person_reference_images(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    save_live_state(
        state_path,
        LiveClipState(
            clip_id="clip-0001",
            step="references_ready",
            reference_image_path=None,
            person_reference_images={"actor_a": Path("work/chatgpt_refs/clip-0001_actor_a.png")},
            rendered_output_path=Path("output/rendered/clip-0001.mp4"),
            runninghub_task_id=None,
            pause_reason=None,
            last_error=None,
            last_screenshot_path=None,
        ),
    )

    restored = load_live_state(state_path)
    assert restored.person_reference_images["actor_a"].as_posix().endswith("clip-0001_actor_a.png")
```

Add a ChatGPT adapter test that one page adapter call can persist a requested output path for one person.

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_chatgpt_page.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_state.py -q`

Expected: FAIL because live state and ChatGPT request models still assume a single reference image.

**Step 3: Write the minimal implementation**

Extend `LiveClipState`:

```python
@dataclass(frozen=True)
class LiveClipState:
    ...
    person_reference_images: dict[str, Path]
    retry_count: int = 0
```

Add a per-person request model:

```python
@dataclass(frozen=True)
class PersonReferenceRequest:
    clip_id: str
    source_person_id: str
    frame_path: Path
    output_path: Path
    prompt: str
```

Keep the adapter contract simple: one request still produces one image, but orchestration now issues one request per person.

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_chatgpt_page.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_state.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/chatgpt_page.py scripts/browser_video_remix/browser_executor.py scripts/browser_video_remix/live_state.py tests/test_browser_video_remix_chatgpt_page.py tests/test_browser_video_remix_live_state.py
git commit -m "feat: persist per-person chatgpt references"
```

### Task 7: Add replacement quality audit models and retry planning

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\replacement_audit.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_replacement_audit.py`

**Step 1: Write the failing tests**

Add finding classification tests:

```python
def test_plan_retry_for_role_swap_requests_different_best_frame() -> None:
    result = ReplacementAuditResult(
        status="retry",
        finding_type="role_swap",
        confidence=0.91,
    )

    action = plan_retry_action(result, attempt=1, max_attempts=3)

    assert action == "choose_alternate_keyframe"
```

Add an exhaustion test:

```python
def test_plan_retry_returns_pause_after_third_failure() -> None:
    result = ReplacementAuditResult(status="retry", finding_type="background_drift", confidence=0.88)

    action = plan_retry_action(result, attempt=3, max_attempts=3)

    assert action == "pause_and_notify"
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_replacement_audit.py -q`

Expected: FAIL because the audit module does not yet exist.

**Step 3: Write the minimal implementation**

Create the audit result and retry planner:

```python
@dataclass(frozen=True)
class ReplacementAuditResult:
    status: str
    finding_type: str
    confidence: float


def plan_retry_action(result: ReplacementAuditResult, attempt: int, max_attempts: int) -> str:
    if attempt >= max_attempts:
        return "pause_and_notify"
    if result.finding_type in {"role_swap", "not_replaced"}:
        return "choose_alternate_keyframe"
    if result.finding_type in {"partial_replace", "background_drift"}:
        return "strengthen_prompt"
    return "resubmit_runninghub"
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_replacement_audit.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/replacement_audit.py tests/test_browser_video_remix_replacement_audit.py
git commit -m "feat: add replacement audit retry planning"
```

### Task 8: Add RunningHub workflow introspection and binding cache

**Files:**
- Create: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\workflow_binding.py`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\fixtures\runninghub_wan_animate_workflow.json`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_workflow_binding.py`

**Step 1: Write the failing tests**

Create a fixture-driven binding test:

```python
def test_inspect_wan_workflow_finds_video_reference_and_optional_control_nodes() -> None:
    workflow = json.loads(
        Path("tests/fixtures/runninghub_wan_animate_workflow.json").read_text(encoding="utf-8")
    )

    binding = inspect_workflow_binding(workflow)

    assert binding.video_node_id is not None
    assert len(binding.reference_node_ids) >= 2
    assert "pose" in binding.optional_controls
```

Add a cache-roundtrip test:

```python
def test_save_and_load_workflow_binding_round_trip(tmp_path: Path) -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_workflow_binding.py -q`

Expected: FAIL because the workflow binding module and fixture do not yet exist.

**Step 3: Write the minimal implementation**

Start with a fixture and a deterministic inspector:

```python
@dataclass(frozen=True)
class WorkflowBinding:
    workflow_id: str
    video_node_id: int | None
    reference_node_ids: list[int]
    optional_controls: dict[str, int]


def inspect_workflow_binding(workflow: dict[str, object]) -> WorkflowBinding:
    ...
```

Add helpers to persist and restore the binding JSON under `work/workflow_bindings/`.

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_workflow_binding.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/workflow_binding.py tests/fixtures/runninghub_wan_animate_workflow.json tests/test_browser_video_remix_workflow_binding.py
git commit -m "feat: add wan workflow binding cache"
```

### Task 9: Extend RunningHub adapter for multiperson workflow binding and control application

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\browser_executor.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py`

**Step 1: Write the failing tests**

Add a multiperson binding test:

```python
def test_runninghub_adapter_uploads_multiple_person_references_and_applies_lora_controls() -> None:
    adapter = RunningHubPageAdapter(workflow_url="https://www.runninghub.cn/workflow/2034283586668466178")
    page = FakeRunningHubPage(graph_api_available=True, graph_task_id="task-123")
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
    )

    result = adapter.submit_render_job(page, request)

    assert result.status == "submitted"
    assert page.graph_uploads[0][1].endswith("clip-0001.mp4")
    assert len(page.graph_uploads) >= 3
```

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py -q`

Expected: FAIL because the adapter still assumes a single reference image and no workflow binding cache.

**Step 3: Write the minimal implementation**

Extend `ClipExecutionRequest`:

```python
@dataclass(frozen=True)
class ClipExecutionRequest:
    ...
    person_reference_images: dict[str, Path]
    lora_controls: dict[str, float]
    workflow_binding_path: Path | None = None
```

Teach `RunningHubPageAdapter.submit_render_job()` to:

- resolve or load a workflow binding
- upload the source video
- upload each mapped person reference image into the bound node set
- apply LoRA or optional control widgets when present
- then queue the prompt and recover `task_id`

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_page.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_runninghub_adapter.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/runninghub_page.py scripts/browser_video_remix/browser_executor.py tests/test_browser_video_remix_runninghub_page.py tests/test_browser_video_remix_runninghub_adapter.py
git commit -m "feat: bind multiperson controls into wan workflow"
```

### Task 10: Extend the live runner for multiperson references, audits, retries, and notifications

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\cli.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py`
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_cli.py`

**Step 1: Write the failing tests**

Add a retry exhaustion test:

```python
def test_run_single_clip_live_flow_pauses_and_notifies_after_three_audit_failures(tmp_path: Path) -> None:
    runninghub_adapter = FakeRunningHubAdapter()
    audit_results = [
        ReplacementAuditResult(status="retry", finding_type="not_replaced", confidence=0.9),
        ReplacementAuditResult(status="retry", finding_type="not_replaced", confidence=0.9),
        ReplacementAuditResult(status="retry", finding_type="not_replaced", confidence=0.9),
    ]

    result = run_single_clip_live_flow(
        ...,
        audit_runner=FakeAuditRunner(audit_results),
    )

    state = load_live_state(state_path)
    assert state.step == "paused"
    assert state.retry_count == 3
    assert (paths.logs_notifications_dir / "clip-0001.json").exists() is True
```

Add a CLI summary test that reports paused notifications.

**Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_cli.py -q`

Expected: FAIL because the live runner does not yet coordinate audits, retries, or notification artifacts.

**Step 3: Write the minimal implementation**

Update the runner to:

- load and persist `retry_count`
- fan out ChatGPT requests per person
- call a reference audit before submission
- call a render audit after download
- use `plan_retry_action()` to choose the next action
- write a notification artifact after the third failed audit

Sketch:

```python
if audit_result.status == "retry":
    next_attempt = existing_retry_count + 1
    if next_attempt >= retry_config.max_attempts:
        write_notification(...)
        persist_state(step="paused", retry_count=next_attempt, ...)
        return build_result(task_id, ...)
    persist_state(step="references_ready", retry_count=next_attempt, ...)
    return retry_clip(...)
```

**Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest pytest D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_runner.py D:\codex-worktrees\browser-video-remix-phase2\tests\test_browser_video_remix_live_cli.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/browser_video_remix/live_runner.py scripts/browser_video_remix/cli.py tests/test_browser_video_remix_live_runner.py tests/test_browser_video_remix_live_cli.py
git commit -m "feat: add audit retries and pause notifications"
```

### Task 11: Add smoke-test docs and a real multiperson workflow verification checklist

**Files:**
- Modify: `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`
- Create: `D:\codex-worktrees\browser-video-remix-phase2\work\run_live_smoke_multiperson.py`

**Step 1: Write the failing documentation checklist**

Update the smoke document to require:

- one dual-person shot
- verified role mapping
- reference audit evidence
- render audit evidence
- pause notification after forced three-failure simulation

**Step 2: Run docs sanity check**

Run: `Get-Content D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`

Expected: The old checklist still only covers single-clip single-reference verification.

**Step 3: Write the minimal implementation**

Add a real smoke helper that:

- opens the configured browser profile
- runs one prepared dual-person shot
- prints the resulting `clip_id`, `task_id`, audit result, and output path

**Step 4: Run the targeted smoke helper**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; $env:RESET_STATE='0'; uv run --with playwright python D:\codex-worktrees\browser-video-remix-phase2\work\run_live_smoke_multiperson.py`

Expected: For a real authenticated environment, the output reaches either `validated` or a deliberate `paused` state with evidence.

**Step 5: Commit**

```bash
git add docs/browser-video-remix-smoke-test.md work/run_live_smoke_multiperson.py
git commit -m "docs: add multiperson remix smoke verification"
```

### Task 12: Final verification and branch handoff

**Files:**
- Verify only

**Step 1: Run the full automated test suite**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; uv run --with pytest --with pyyaml --with scenedetect --with numpy --with opencv-contrib-python pytest D:\codex-worktrees\browser-video-remix-phase2\tests -q`

Expected: PASS

**Step 2: Run one authenticated multiperson smoke clip**

Run: `$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'; $env:RESET_STATE='0'; uv run --with playwright python D:\codex-worktrees\browser-video-remix-phase2\work\run_live_smoke_multiperson.py`

Expected:

- the shot reaches `validated` or a precise `paused` state
- retries never exceed three
- notification evidence is written if the shot pauses after retry exhaustion

**Step 3: Review the final changed files**

Verify:

- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\config.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\shot_splitter.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\identity_registry.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\face_analysis.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\keyframe_selection.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\workflow_binding.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\replacement_audit.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\live_runner.py`
- `D:\codex-worktrees\browser-video-remix-phase2\scripts\browser_video_remix\runninghub_page.py`
- `D:\codex-worktrees\browser-video-remix-phase2\docs\browser-video-remix-smoke-test.md`

**Step 4: Commit the final integration changes**

```bash
git add scripts/browser_video_remix tests docs/browser-video-remix-smoke-test.md work/run_live_smoke_multiperson.py
git commit -m "feat: complete multiperson browser remix automation"
```

**Step 5: Push or hand off**

At this point the branch should contain:

- config + manifest upgrades
- local shot segmentation
- multiperson identity and keyframe selection
- workflow binding and multiperson RunningHub submission
- reference and render quality audits
- three-attempt retry with pause notification

The branch is then ready for the same finish flow already used in this repository.
