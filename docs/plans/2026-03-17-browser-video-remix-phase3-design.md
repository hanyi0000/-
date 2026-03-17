# Browser Video Remix Phase 3 Live Browser Design

**Date:** 2026-03-17
**Status:** Approved

## Goal

Extend the current browser video remix scaffold into a real single-clip browser automation flow that can drive both ChatGPT and RunningHub with a dedicated browser profile, pause for manual intervention when needed, and resume from disk-backed state.

## Scope

### In Scope

- Real Playwright browser startup with a dedicated persistent profile.
- Real ChatGPT page actions for one clip:
  - open page
  - verify session
  - upload frame
  - submit prompt
  - save the generated reference image
- Real RunningHub page actions for one clip:
  - open fixed workflow URL
  - verify session
  - upload source clip and reference image
  - set resolution fields
  - submit the workflow
  - capture task ID
  - poll completion
  - download the rendered clip
- Disk-backed live state for pause and resume.
- Explicit operator pause flow for login expiry, captcha, and UI drift.
- Manual smoke test for one authenticated clip run.

### Out of Scope

- Multi-clip batch execution.
- Automated login or captcha solving.
- Dialogue rewrite and voice conversion.
- Final merge in Jianying.
- Full selector hardening for every possible UI variation.

## Selected Approach

Use two real page adapters behind a single-clip live runner. The runner owns state progression and recovery, while each page adapter owns selectors, waits, and browser-specific failure detection. When the browser flow hits a manual boundary, the system pauses without tearing down the browser, writes the current live state to disk, and waits for the operator to recover the session before resuming.

This is the smallest step that proves the real browser path without overcommitting to batch orchestration before the fragile parts are stable.

## Architecture

### Dedicated Browser Profile

The browser launches from a dedicated persistent profile directory rather than reusing the user's day-to-day browser profile. This isolates automation state, avoids incidental tab interference, and makes session debugging reproducible.

### Single-Clip Live Runner

The live runner executes one clip through a fixed sequence:

1. prepare clip inputs
2. open ChatGPT
3. verify ChatGPT session
4. upload frame and submit prompt
5. wait for reference image
6. save reference image
7. open RunningHub
8. verify RunningHub session
9. upload video and reference image
10. set resolution and fixed fields
11. submit workflow
12. capture task ID
13. poll until terminal state
14. download rendered clip
15. validate final output

Each step records success to disk before the next step begins.

### Page Adapter Boundary

The runner never directly manipulates selectors. It calls high-level adapter methods such as:

- `ensure_session()`
- `submit_reference_generation()`
- `save_reference_image()`
- `submit_render_job()`
- `poll_render_status()`
- `download_render_output()`

This keeps site drift isolated to the adapter layer.

## Live State and Resume Design

Each clip stores a live state file under `work/live_state/<clip_id>.json`. The file tracks:

- current step
- clip paths
- reference image path
- rendered output path
- RunningHub task ID
- pause reason
- last error code
- last screenshot path
- timestamps for the latest successful step

Pause is an explicit persisted state, not an unhandled exception. A paused run can be resumed from the last successful step without redoing completed browser work.

Resume rules:

- if the ChatGPT reference image already exists and the state marks it complete, do not regenerate it
- if a RunningHub task ID already exists, continue polling instead of resubmitting
- if the rendered output already exists and validates, stop and mark the clip done

## Operator Pause Model

The system pauses immediately when it detects any of the following:

- login required
- captcha required
- selector missing
- page structure changed
- manual confirmation required

On pause, the system must:

- write the live state
- capture a screenshot
- capture the current page URL
- log the exact pause reason
- leave the browser session alive for operator intervention when possible

After the operator fixes the issue, the user reruns the resume command and the runner continues from the last completed step.

## Component Responsibilities

### Playwright Driver

- launch persistent browser context
- create pages on demand
- manage download directory
- expose browser session handles to adapters

### ChatGPT Adapter

- open the configured ChatGPT page
- detect whether the session is valid
- upload the extracted frame
- submit the rendered prompt
- wait for image output
- save the result to `work/chatgpt_refs/`
- classify login, captcha, and selector failures

### RunningHub Adapter

- open the configured workflow URL
- detect whether the session is valid
- upload clip and reference image
- apply resolution and fixed workflow fields
- submit the job
- capture task ID
- poll task progress
- download the final clip to a controlled output path

### Live Runner

- orchestrate one clip end to end
- persist live state after every step
- decide whether to continue, pause, or resume
- invoke validation after download

## Configuration Additions

Phase 3 should extend config support for live browser runs with:

- ChatGPT start URL
- RunningHub workflow URL
- browser profile directory
- browser headless mode
- default wait timeouts
- poll interval for RunningHub task refresh
- download directory settings

The first version should avoid configurable selectors unless a real mismatch forces that need.

## Error Handling

The design distinguishes three classes of failure:

### Recoverable Pause

- login expired
- captcha presented
- temporary page block

Action: pause and wait for manual recovery.

### Recoverable Retry

- transient upload delay
- delayed task status refresh
- delayed download appearance

Action: bounded condition-based retry.

### Hard Failure

- required selector missing after retry
- invalid downloaded file
- repeated terminal RunningHub failure

Action: persist failure state and stop the single-clip run.

## Testing Strategy

Automated tests should cover:

- live state persistence and resume decisions
- pause reason classification
- single-clip step sequencing
- adapter behavior against mocked Playwright-like page objects

Manual verification should cover one authenticated real run using:

- one short clip
- one extracted frame
- one complete ChatGPT reference generation
- one complete RunningHub render and download

## Deliverables

Phase 3 should produce:

- a real Playwright-backed browser session bootstrap
- a single-clip live runner
- ChatGPT and RunningHub live adapters
- pause and resume support with disk-backed state
- an updated smoke test for a real browser-authenticated run
