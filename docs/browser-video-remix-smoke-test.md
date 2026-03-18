# Browser Video Remix Smoke Test

## Goal

Verify the browser video remix pipeline can run one clip end to end before attempting a full batch.

## Prerequisites

- Python available at `F:\anconda3\python.exe`
- `pytest` available in that environment
- `ffmpeg` and `ffprobe` available on `PATH`
- Playwright and browser dependencies installed before real browser automation work begins
- A persistent browser profile available for authenticated ChatGPT and RunningHub sessions

## Project Setup Checklist

1. Create a project directory under the chosen D drive workspace.
2. Place the raw input video under `input/`.
3. Create `config.yaml` with:
   - source video path
   - actor to character mappings
   - reference image paths
   - resolution rules
   - RunningHub workflow URL and fixed parameters
4. Confirm all referenced files exist before running any batch command.

## Dry-Run Checklist

1. Run the current test suite:

```powershell
& 'F:\anconda3\python.exe' -m pytest -q
```

2. Confirm all tests pass.
3. Verify the current planning helpers before live browser work:
   - confirm `build_project_paths()` resolves the expected project layout
   - confirm `plan_prepare_run()` points to `work/clips`, `work/frames`, and `work/manifest.json`
   - confirm `build_single_clip_flow_summary()` points to the expected manifest and rendered output target
   - confirm `build_live_run_request()` points to `work/live_state/<clip_id>.json` and `work/downloads`

## Single-Clip Browser Smoke Test

Use one short clip only.

1. Prepare one clip and one extracted frame.
2. Build a one-clip summary and confirm:
   - the manifest target ends with `work/manifest.json`
   - the rendered output target ends with `output/rendered/<clip_id>.mp4`
3. Build the live run request and confirm:
   - the state file target ends with `work/live_state/<clip_id>.json`
   - the download directory target ends with `work/downloads`
4. Launch the browser executor with a persistent profile.
5. Confirm ChatGPT opens with the authenticated session intact.
6. Upload the frame and submit the generated prompt.
7. Confirm one reference image is produced and saved to the expected working directory.
8. Open the configured RunningHub workflow page.
9. Upload the clip and reference image.
10. Confirm the submitted resolution matches the clip resolution.
11. Submit the workflow and capture the returned task ID.
12. Wait for completion and download the rendered clip.
13. Confirm the output lands in the rendered output directory with the expected clip ID.

## Resume Checklist

1. Stop the process after one successful step.
2. Restart the pipeline.
3. Confirm the live state file records the last completed step and any pause reason.
4. Confirm already completed steps are skipped.
5. Confirm failed or incomplete steps remain pending.

## Validation Checklist

1. Confirm missing outputs are reported explicitly.
2. Confirm output files are grouped into success and failure destinations.
3. Confirm logs and screenshots are retained for failed browser steps.
4. Confirm the final report lists ready clips and failed clips separately.

## Exit Criteria

Do not run a full sequence until:

- tests are green
- dry-run metadata looks correct
- one clip completes through ChatGPT and RunningHub
- resume behavior is verified
- output validation reports the expected result
