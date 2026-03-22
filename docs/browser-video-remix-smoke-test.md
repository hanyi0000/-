# Browser Video Remix Multiperson Smoke Test

## Goal

Verify the multiperson browser remix pipeline can process one prepared shot end to end, persist per-person references, apply workflow bindings, and either validate or pause with explicit audit evidence before attempting a larger batch.

## Prerequisites

- Python available in the repo environment
- `pytest`, `Playwright`, `ffmpeg`, and `ffprobe` available
- A persistent browser profile available for authenticated ChatGPT and RunningHub sessions
- One prepared shot under `work/shots/` or a fallback smoke clip under `work/clips/`
- Two prepared person keyframes under `work/keyframes/` or explicit frame-path overrides

## Project Setup Checklist

1. Prepare one dual-person shot and preserve a stable `clip_id`.
2. Confirm the target role mapping is fixed before the smoke begins.
3. Confirm each source person has at least one usable keyframe candidate.
4. Confirm the target RunningHub workflow URL is the Wan Animate workflow under test.
5. Confirm the workflow binding cache is either present under `work/workflow_bindings/` or can be rebuilt from the live workflow.

## Dry-Run Checklist

1. Run the current automated test suite subset or full suite.
2. Confirm the planning helpers now point to shot-based paths:
   - `plan_prepare_run()` resolves `work/shots`, `work/keyframes`, and `work/manifest.json`
   - `build_live_run_request()` resolves `work/live_state/<clip_id>.json` and `work/downloads`
   - `build_live_run_summary()` resolves `logs/notifications/<clip_id>.json`
3. Confirm the workflow binding fixture detects:
   - one source video node
   - multiple reference image nodes
   - optional controls such as `pose` and LoRA widgets

## Multiperson Browser Smoke Test

Use one prepared shot only.

1. Build or confirm a shot-level manifest entry with:
   - `clip_id`
   - `start_ms` / `end_ms`
   - `retry_count`
   - `person_reference_images`
2. Confirm the shot has one person frame for each mapped source identity.
3. Launch the smoke helper:

```powershell
$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'
$env:RESET_STATE='0'
uv run --with playwright python D:\codex-worktrees\browser-video-remix-phase2\work\run_live_smoke_multiperson.py
```

4. Confirm the helper reports:
   - the chosen shot path
   - the chosen per-person frame paths
   - the resulting `clip_id`
   - the RunningHub `task_id`
   - the final live-state step
5. Confirm one reference image is produced for each person and saved under `work/chatgpt_refs/`.
6. Confirm the reference audit step runs before RunningHub submission.
7. Confirm the RunningHub submission uploads:
   - the source shot
   - each per-person reference image
   - any mapped LoRA control values from the workflow binding
8. Confirm the render audit step runs after download.
9. Confirm the final state is either:
   - `validated`, or
   - a deliberate `paused` state with a precise pause reason and evidence

## Forced Retry / Notification Checklist

1. Re-run the smoke helper with three forced render-audit failures:

```powershell
$env:PYTHONPATH='D:\codex-worktrees\browser-video-remix-phase2'
$env:RESET_STATE='1'
$env:FORCE_RENDER_AUDIT_FAILURES='3'
uv run --with playwright python D:\codex-worktrees\browser-video-remix-phase2\work\run_live_smoke_multiperson.py
```

2. Confirm retries never exceed three attempts.
3. Confirm the final live state is `paused`.
4. Confirm a notification artifact is written under `logs/notifications/<clip_id>.json`.
5. Confirm the notification JSON includes the audit finding type, retry count, and selected action.

## Pause Evidence Checklist

1. If RunningHub pauses, confirm pause evidence is written under `logs/runninghub-pauses/<clip_id>/`:
   - `pause.png`
   - `pause.html`
   - `pause.json`
2. Confirm `work/live_state/<clip_id>.json` records:
   - `last_screenshot_path`
   - `person_reference_images`
   - `retry_count`

## Exit Criteria

Do not run a larger multiperson batch until:

- automated tests are green
- one shot completes the multiperson path or pauses with explicit evidence
- per-person references persist correctly
- workflow binding uploads all required inputs
- render-audit retries stop at three attempts
- notification evidence is written for forced retry exhaustion
