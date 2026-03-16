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
3. Run the future batch command in dry-run mode once the CLI is wired:
   - verify project path resolution
   - verify manifest count
   - verify no browser submission happens

## Single-Clip Browser Smoke Test

Use one short clip only.

1. Prepare one clip and one extracted frame.
2. Launch the browser executor with a persistent profile.
3. Confirm ChatGPT opens with the authenticated session intact.
4. Upload the frame and submit the generated prompt.
5. Confirm one reference image is produced and saved to the expected working directory.
6. Open the configured RunningHub workflow page.
7. Upload the clip and reference image.
8. Confirm the submitted resolution matches the clip resolution.
9. Submit the workflow and capture the returned task ID.
10. Wait for completion and download the rendered clip.
11. Confirm the output lands in the rendered output directory with the expected clip ID.

## Resume Checklist

1. Stop the process after one successful step.
2. Restart the pipeline.
3. Confirm already completed steps are skipped.
4. Confirm failed or incomplete steps remain pending.

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
