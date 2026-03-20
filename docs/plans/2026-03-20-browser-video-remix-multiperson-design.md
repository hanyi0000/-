# Browser Video Remix Multiperson Automation Design

**Date:** 2026-03-20
**Status:** Approved

## Goal

Extend the existing browser-first remix pipeline into a multiperson, project-driven automation flow that:

- splits one source video into real shots locally
- tracks multiple source identities across the full video
- selects the best frontal frame per source person per shot
- generates per-person replacement references with ChatGPT
- drives the specified RunningHub `Wan Animate_Mix_KJ` workflow
- verifies that replacement actually succeeded
- retries bad outputs up to three times before pausing and notifying the operator

## Confirmed Requirements

The approved workflow is:

1. Start from one raw source video.
2. Perform local automatic shot segmentation without relying on Jianying.
3. Support multiple people in the same shot.
4. Use full-video fixed mapping: each source person always maps to the same target role.
5. Accept user-provided source-person sample images and target-role assets.
6. Still auto-select the best frontal frame for each mapped source person inside each shot.
7. Support target-role strategies per role:
   - `prompt_only`
   - `reference_pack`
   - `lora`
   - `hybrid`
8. Use ChatGPT to generate replacement reference images.
9. Use the RunningHub workflow at `https://www.runninghub.cn/workflow/2034283586668466178`.
10. Automatically fill required workflow inputs and controls, including multiperson reference assets and workflow-specific controls such as mask / pose / motion-related inputs when available.
11. Poll RunningHub, download outputs, and support resume.
12. Audit both reference images and rendered outputs for real replacement quality.
13. Retry failed quality checks automatically up to three times, then pause and notify.

## Scope

### In Scope

- Local shot boundary detection.
- Project-level source identity registry and target role registry.
- Multiperson identity matching within each detected shot.
- Best-frame extraction for each mapped person.
- Per-person ChatGPT reference generation and persistence.
- RunningHub workflow introspection and binding cache for the target Wan Animate workflow family.
- Multiperson workflow submission, polling, download, and resume.
- Replacement quality auditing for both image and video outputs.
- Automatic retry orchestration with evidence capture and pause state.

### Out of Scope for This Iteration

- Generic support for every RunningHub or ComfyUI workflow.
- Automatic dialogue rewriting or voice conversion.
- Final multi-shot timeline assembly in Jianying.
- Autonomous aesthetic judgment beyond explicit audit rules.
- Zero-touch initialization for brand new projects. The operator still provides source-person images, target-role assets, and confirms the project mapping once.

## Primary Target Workflow

The current target is the RunningHub workflow advertised in the referenced tutorial:

- Workflow URL: `https://www.runninghub.cn/workflow/2034283586668466178`
- Public work page: `https://www.runninghub.cn/post/1994708135476596738/?inviteCode=rh-v1333`
- Tutorial: `https://www.bilibili.com/video/BV15LS1BCEh5/`

This workflow is treated as the primary supported workflow for V1. The implementation should avoid hard-coding every node id where possible, but it is acceptable to keep the first version specialized to this workflow family.

## Architecture

### 1. Shot Segmentation Layer

The pipeline first converts one source video into a stable shot manifest using local shot boundary detection. The output unit remains the existing `clip_id`, but each `clip_id` now represents one detected shot rather than a fixed-duration slice.

Responsibilities:

- detect shot boundaries locally
- export shot clips under `work/shots/`
- store time ranges and metadata in the manifest
- support importing an externally prepared cut list later without changing downstream stages

### 2. Identity Layer

The operator provides sample images for the source people that should be replaced and assets for the target roles. The system builds a project-level identity index so each detected face in a shot can be matched back to a stable source person id.

Responsibilities:

- load source-person anchor images
- load target-role assets and strategy settings
- preserve one fixed `source_person_id -> target_role_id` mapping across the entire project

### 3. Best Frontal Frame Layer

For each detected shot, the system tracks known source people across frames and selects the best frontal frame per person for reference generation.

Selection criteria:

- face size
- frontal angle
- image sharpness
- low occlusion
- temporal stability

This keeps ChatGPT input quality stable and reduces bad role replacement caused by side faces, blurred faces, or partial occlusion.

### 4. Reference Generation Layer

ChatGPT generation moves from a single frame-per-shot model to a per-person reference model. Each mapped person in a shot gets its own replacement reference image, persisted under a deterministic path.

Responsibilities:

- build one reference request per person
- apply target-role strategy:
  - `prompt_only`
  - `reference_pack`
  - `lora`
  - `hybrid`
- save per-person outputs
- run a reference audit before RunningHub submission

### 5. Workflow Introspection and Binding Layer

The RunningHub adapter must stop assuming one video node plus one reference image node. Instead, it should read the authenticated workflow content, identify relevant upload nodes and control widgets, and cache the binding result for reuse.

Responsibilities:

- fetch workflow content in an authenticated browser session
- identify video input nodes, person-reference nodes, pose inputs, mask inputs, LoRA controls, and motion-related widgets when present
- cache the resolved binding under `work/workflow_bindings/`
- fail with precise evidence when required bindings cannot be resolved

### 6. Execution Layer

The live runner remains the orchestrator but now executes one shot task with multiple person substeps.

Responsibilities:

- skip completed stages on resume
- avoid duplicate ChatGPT generation and duplicate RunningHub submission
- persist submission ids and retry history
- download final renders and validate them

### 7. Quality Audit and Retry Layer

This is the critical addition for production usability. The pipeline should not treat any completed file as automatically correct.

Audit phases:

- `reference audit` after ChatGPT output
- `render audit` after RunningHub output

Failure types to detect:

- replacement did not happen
- target roles were swapped between people
- only a local patch happened instead of full intended replacement
- background changed too much
- pose or scene structure drifted beyond allowed thresholds

Retry behavior:

1. switch to another top-ranked frontal frame
2. strengthen or clarify the prompt
3. escalate strategy from prompt-only toward reference or LoRA usage when configured
4. resubmit to RunningHub

After three failed attempts for the same shot, the system pauses and notifies the operator with saved evidence.

## Project Data Model

The project config must evolve from the current simple actor map into a richer project definition.

Suggested top-level sections:

- `source_video`
- `segmentation`
- `browser`
- `chatgpt`
- `runninghub`
- `vision`
- `source_identities`
- `target_roles`
- `identity_mapping`
- `quality_audit`
- `retry`

Suggested working directories:

- `assets/source_people/`
- `assets/target_roles/`
- `work/shots/`
- `work/shot_manifest.json`
- `work/face_detections/`
- `work/keyframes/`
- `work/chatgpt_refs/`
- `work/workflow_bindings/`
- `work/live_state/`
- `work/quality_reports/`
- `logs/notifications/`

## State Model

Each shot task should advance through explicit states:

- `shot_detected`
- `identities_bound`
- `keyframes_ready`
- `references_ready`
- `workflow_bound`
- `runninghub_submitted`
- `runninghub_polling`
- `downloaded`
- `validated`
- `paused`
- `failed`

The state file must also record:

- retry count
- last audit finding
- per-person reference image paths
- resolved workflow binding cache path
- last screenshot / HTML / summary evidence paths

## Quality Audit Design

### Reference Audit

Input:

- source-person anchor image
- target-role anchor assets
- selected best frontal frame
- generated ChatGPT reference image

Checks:

- output is closer to target role than to source person
- person identity is not swapped
- background drift outside the person region is below threshold
- replacement is not only a partial facial patch

### Render Audit

Input:

- original shot video
- final rendered shot video
- mapped source and target identities

Checks:

- sampled render frames contain the correct target role for each mapped person
- expected source person no longer dominates the output
- multiperson assignments are not inverted
- background drift stays below threshold outside active people regions

The audit result produces structured findings, not only a boolean outcome. Retry policy is driven by the dominant finding type.

## Testing Strategy

The implementation should stay TDD-driven and keep the current repository style.

### Unit Tests

- config loading
- shot manifest persistence
- strategy resolution
- retry planning
- state transitions
- audit rule evaluation

### Contract Tests

- sanitized RunningHub workflow fixture
- workflow introspection and binding
- multiperson node assignment

### Adapter Tests

- ChatGPT multiperson reference submission
- RunningHub multiperson upload and control application
- resume behavior with existing task ids and cached bindings

### Live Smoke Tests

- one dual-person shot through the full browser path
- one more complex shot with overlapping people
- evidence capture and automatic pause after three audit failures

## Risks and Mitigations

### Workflow Drift

Risk:
RunningHub changes node titles, order, or cached graph shape.

Mitigation:
Use workflow introspection plus cached bindings, not only hard-coded node ids. Fail with binding evidence before submission.

### Identity Drift in Crowded Shots

Risk:
Multiple similar faces or heavy occlusion may cause wrong person matching.

Mitigation:
Use project-level anchor images, per-shot tracking confidence, and explicit risk flags when confidence falls below threshold.

### Prompt-Only Instability

Risk:
Pure prompt mode may not preserve target identity consistently.

Mitigation:
Support `reference_pack`, `lora`, and `hybrid` per role. Retry planner may escalate to stronger configured assets automatically.

### False Success

Risk:
The pipeline may produce a file that exists but is visually wrong.

Mitigation:
Gate success on audit results, not only download success.

## Success Criteria

The feature is considered complete only when all of the following are true:

1. A project can be configured with multiple source people and multiple target roles.
2. The pipeline can detect shots locally from one source video.
3. The pipeline can identify mapped source people in each shot and choose best frontal frames.
4. ChatGPT can generate per-person references and persist them deterministically.
5. RunningHub can accept the shot video plus per-person control inputs for the target Wan Animate workflow.
6. The pipeline can poll, download, resume, and validate without redoing completed work.
7. Quality audit can detect the major bad-output classes discussed with the operator.
8. Three failed retries pause the shot and produce evidence plus notification artifacts.
