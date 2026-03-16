# Browser Video Remix Automation Design

**Date:** 2026-03-17
**Status:** Approved

## Goal

Build a browser-first automation pipeline for film/TV remix production that starts from one raw video, automates clip preparation and browser task execution, and produces a validated set of rendered clips ready for final assembly in Jianying.

## User Workflow Today

The current process is:

1. Split source footage into short clips in Jianying.
2. Capture one frame from each clip.
3. Use the ChatGPT web app to replace original actors in the frame with target remix characters, such as Valorant characters.
4. Use a RunningHub workflow to replace all characters in each video clip based on the reference image.
5. Save each rendered clip, repeat until the full sequence is finished, and then merge clips in Jianying.
6. Later, rewrite dialogue and apply voice conversion.

The user wants the first version to focus on the highest-effort repeated work and keep Jianying only for final editing and merging.

## Scope

### In Scope for V1

- Start from one raw source video.
- Automatically split the raw video into clips.
- Extract a reference frame for each clip.
- Drive the ChatGPT web app to generate character-replaced reference images.
- Drive a fixed RunningHub workflow in the browser for each clip.
- Pass clip video, reference image, resolution settings, and prompt fields into RunningHub.
- Poll task status, download finished clips, and store them in a stable output structure.
- Validate outputs and generate a failure report.
- Support resume from interruption without rerunning completed clips.

### Out of Scope for V1

- Dialogue rewriting.
- Voice conversion.
- Automatic final merge inside Jianying.
- Automatic discovery of unknown actors.
- Replacing RunningHub with a local or API renderer.

## Key Constraints

- The user prefers a browser-first automation model because the critical production steps already happen in browser tools.
- RunningHub remains the rendering backend in V1.
- Character mapping is stable at the project level: Actor A always maps to Character A, Actor B always maps to Character B.
- Output quality depends heavily on matching image and video resolution correctly.
- Browser automation must tolerate UI changes, upload delays, and partial failures.

## Selected Approach

Use a local Python orchestrator with Playwright-controlled browser sessions. The local system handles clip preparation, job bookkeeping, validation, and resume logic. The browser executor handles only the steps that must remain on ChatGPT and RunningHub.

This is the smallest design that preserves the user's current toolchain while removing the highest-cost repetitive work. It also creates a clean seam for future migration away from browser-only tooling if RunningHub later exposes stable APIs.

## Architecture

### 1. Project-Driven Batch Execution

Each remix job is stored under a dedicated project directory containing:

- the source video
- actor-to-character mappings
- character reference assets
- prompt templates
- resolution rules
- browser workflow configuration

The pipeline reads this project config and generates one task record per clip.

### 2. Local Media Preparation

Before the browser is involved, the system:

- reads the raw source video
- splits it into clips using configured rules
- extracts a reference frame from each clip
- records clip metadata such as duration, width, height, and frame rate

This reduces manual work in Jianying and ensures downstream tasks receive normalized inputs.

### 3. Browser Execution Layer

The browser executor runs a deterministic sequence per clip:

- open or reuse authenticated ChatGPT session
- upload the clip frame
- submit a structured prompt describing actor-to-character replacements
- save the generated reference image
- open the fixed RunningHub workflow
- upload the clip video and generated reference image
- set resolution and prompt fields
- submit the workflow
- poll for completion
- download the rendered clip

### 4. Validation and Recovery Layer

Every major step writes task state to disk. The system can resume from the latest successful checkpoint. Failed clips are isolated and do not block the remaining batch.

## Component Design

### Project Configuration

The project config will define:

- source video path
- clip splitting strategy
- actor-to-character mappings
- character asset paths
- prompt templates
- RunningHub page URL and fixed parameter values
- resolution adaptation rules
- retry and timeout settings

### Task Manifest

Each clip gets a manifest entry containing:

- clip ID
- clip file path
- extracted frame path
- intended actor mappings
- target characters
- expected resolution
- ChatGPT prompt payload
- RunningHub submission fields
- execution state

### Browser Session Management

The automation should keep browser sessions warm when possible to reduce repeated logins and page setup cost. It must also detect session expiry and pause for user intervention instead of blindly failing the full batch.

### Download and Output Management

Downloaded files must be renamed to stable clip IDs and stored separately from temporary browser downloads. Output directories should clearly separate successful clips, failed clips, logs, and reports.

## Data Flow

1. User creates a project config and places the raw source video into the project input folder.
2. The pipeline splits the source into ordered clips.
3. The pipeline extracts a frame for each clip.
4. The pipeline creates or updates the task manifest.
5. The browser executor generates one reference image per clip in ChatGPT.
6. The browser executor submits one RunningHub task per clip.
7. The pipeline downloads finished outputs and validates them.
8. The pipeline writes a batch report listing ready clips and failures.
9. The user imports the validated clips into Jianying for final merge.

## Resolution Strategy

Resolution handling is a hard rule in this design.

- Clip metadata is collected immediately after splitting.
- Extracted frames inherit the clip aspect ratio.
- Character assets are normalized when registered in the project.
- Before each RunningHub submission, the system checks whether the clip, frame, and reference image satisfy configured aspect-ratio and resolution rules.
- When needed, the pipeline applies predefined resize, crop, or pad behavior instead of ad hoc manual edits.

This ensures the same project uses one consistent resolution policy across all clips.

## Error Handling

The design must explicitly handle the following failure classes:

- browser element not found
- upload failure
- slow generation timeout
- ChatGPT image generation failure
- RunningHub submission failure
- RunningHub task timeout
- download failure
- output validation failure

For each failure, the system should:

- capture a screenshot when relevant
- write a structured error entry
- mark the clip with a precise state
- continue processing other clips when safe
- allow later resume from the failed state

## Testing Strategy

V1 should include tests for the parts that do not require live browser services:

- project config loading and validation
- clip manifest generation
- resolution rule evaluation
- state transitions for task execution
- resume behavior from partial state
- output validation logic

Browser-specific behavior should be covered with mocked interfaces where possible and a small manual smoke test checklist for real sessions.

## Risks and Mitigations

### Browser UI Drift

Risk: ChatGPT or RunningHub page structure changes and selectors break.

Mitigation: centralize selectors, add screenshot logging, and fail at clip scope rather than batch scope.

### Authentication Expiry

Risk: sessions expire mid-run.

Mitigation: keep persistent browser profiles and pause for re-authentication when detected.

### Inconsistent Output Quality

Risk: mismatched resolutions or prompt drift reduce remix quality.

Mitigation: enforce config-driven resolution rules and use fixed prompt templates with limited parameterized slots.

### Long Batch Runs

Risk: the pipeline may run for hours on a full sequence.

Mitigation: checkpoint every clip and avoid rerunning successful work.

## Deliverables

V1 should produce:

- a project-based browser automation tool
- validated clip outputs ready for Jianying merge
- a failure queue for manual follow-up
- logs, screenshots, and a batch report for traceability
- a manual smoke test checklist for one real browser session before full-batch use

## File Planning

The implementation plan should target:

- `scripts/browser_video_remix/` for the automation code
- `tests/` for unit coverage around config, manifest, state, and validation
- `docs/plans/2026-03-17-browser-video-remix-automation.md` for the implementation plan
