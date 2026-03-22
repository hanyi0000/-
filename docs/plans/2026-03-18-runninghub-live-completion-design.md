# RunningHub Live Completion Design

**Date:** 2026-03-18
**Status:** Approved

## Context

The ChatGPT browser path is now validated for real frame upload and prompt submission. The remaining gap in the single-clip browser workflow is RunningHub: submitting the real workflow, persisting the task identity, polling completion, downloading the rendered clip, and resuming safely after interruption.

This design narrows Phase 3 to one concrete target: complete one authenticated clip from ChatGPT reference generation through RunningHub render download with disk-backed pause and resume.

## Goal

Complete the single-clip browser flow through RunningHub so the live runner can:

- upload the source clip and ChatGPT reference image
- set the correct resolution fields
- submit the fixed workflow
- capture and persist the returned task ID
- poll until the job reaches a terminal state
- download the rendered mp4 into `output/rendered/<clip_id>.mp4`

## Scope

### In Scope

- Real RunningHub workflow submission for one clip.
- Explicit RunningHub session validation before submission.
- Resolution field population and read-back verification.
- Task ID extraction and disk persistence.
- Polling task status until `pending`, `running`, `done`, or `failed`.
- Downloading the rendered clip after terminal success.
- Resume behavior that skips resubmission when a task ID is already known.
- Failure evidence capture with screenshot, HTML, and JSON summary.

### Out of Scope

- Multi-clip batch execution.
- Auto-solving login, captcha, or anti-bot checks.
- Dynamic workflow authoring or per-run field discovery beyond the fixed workflow.
- Full selector hardening for every possible RunningHub layout variant.

## Selected Approach

Keep the live runner as the orchestrator and make the RunningHub adapter responsible for all page-specific logic. The adapter will expose one method per stage rather than a single large procedural script:

- `ensure_session()`
- `submit_render_job()`
- `poll_render_status()`
- `download_render_output()`
- `capture_failure_snapshot()`

The runner owns persisted step transitions and resume rules. The adapter owns selectors, bounded waits, and pause classification.

## Data Flow

1. ChatGPT finishes and writes the reference image path.
2. The runner builds a `ClipExecutionRequest` containing:
   - source clip path
   - reference image path
   - target prompt
   - width
   - height
3. RunningHub submission uploads the clip and image, writes the workflow fields, and returns `task_id`.
4. The runner saves state as `runninghub_submitted`.
5. Polling continues from `task_id` until a terminal status is reached.
6. On success, the adapter downloads the rendered clip to `output/rendered/<clip_id>.mp4`.
7. The runner validates the download and marks the clip `done`.

## State and Resume Design

The existing `LiveClipState` structure remains the persistence anchor, but the runner will start writing more specific step values:

- `runninghub_submitted`
- `runninghub_polling`
- `render_downloaded`
- `done`

Resume rules:

- if `runninghub_task_id` already exists, never resubmit the workflow
- if the state is `runninghub_submitted` or `runninghub_polling`, resume directly from polling
- if the rendered output already exists and validates, mark the clip `done`
- if the browser pauses for login, captcha, or selector drift, keep the last good task ID on disk

## Selector Strategy

Selector lookup is stage-based rather than global:

1. workflow page open and session check
2. source clip upload region
3. reference image upload region
4. width and height fields
5. submit control
6. task list or task detail region
7. download control

Priority order for selectors:

1. stable attributes such as `data-*`, `name`, or `id`
2. explicit button text
3. local structural fallback within the current stage container

The adapter must distinguish video and image upload slots explicitly and never assume there is only one file input on the page.

## Success and Failure Rules

### Success

The workflow is only considered successful when all of the following are true:

- a non-empty `task_id` is captured
- polling reaches `done`
- the final file is downloaded to `output/rendered/<clip_id>.mp4`
- the downloaded file exists, has the expected suffix, and size is greater than zero

### Retry

Bounded retry is allowed only for:

- delayed upload visibility
- delayed task refresh
- delayed download button appearance

### Pause

Pause immediately when:

- login is required
- captcha or challenge is detected
- required selectors are missing after bounded retry
- the page structure is materially different from the expected stage

On pause, save:

- live state
- screenshot
- page HTML
- current URL
- short JSON summary

### Hard Failure

Stop the clip as failed when:

- RunningHub returns a terminal failed status
- download completes but the file is invalid
- no task ID can be extracted after a confirmed submission attempt

## Testing Strategy

### Automated

- page adapter unit tests for:
  - login pause
  - selector drift pause
  - source clip upload
  - reference image upload
  - resolution read-back verification
  - task ID extraction
  - polling state classification
  - download button missing
  - failed terminal status
- live runner tests for:
  - ChatGPT success -> RunningHub submit -> poll -> download -> done
  - resume from existing `runninghub_task_id` without resubmission
  - pause persistence with screenshot and task ID retention

### Manual

- authenticated single-clip smoke test
- one deliberate interruption after submission
- one resume that continues from polling and finishes download

## Deliverables

- upgraded `RunningHubPageAdapter` with staged browser actions
- result models for submission, polling, and download
- live runner state progression through RunningHub completion
- resume-safe reuse of persisted `task_id`
- failure evidence capture for RunningHub pauses
- updated smoke test documentation for the full single-clip loop
