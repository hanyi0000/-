import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.browser_video_remix.chatgpt_page import ChatGptPageAdapter
from scripts.browser_video_remix.live_runner import LiveClipRequest, run_single_clip_live_flow
from scripts.browser_video_remix.live_state import load_live_state
from scripts.browser_video_remix.paths import build_project_paths
from scripts.browser_video_remix.playwright_driver import (
    PersistentContextRequest,
    launch_persistent_context,
)
from scripts.browser_video_remix.replacement_audit import ReplacementAuditResult
from scripts.browser_video_remix.runninghub_page import RunningHubPageAdapter


REPO = Path(r"D:/codex-worktrees/browser-video-remix-phase2")
WORKFLOW_URL = "https://www.runninghub.cn/workflow/2034283586668466178"
CHATGPT_URL = "https://chatgpt.com/"
DEFAULT_EDGE_EXECUTABLE = Path(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
CLIP_ID = os.environ.get("MULTIPERSON_CLIP_ID", "smoke-multiperson")


class ForcedAuditRunner:
    def __init__(self, *, forced_render_failures: int) -> None:
        self.forced_render_failures = forced_render_failures
        self.render_calls = 0
        self.reference_calls = 0

    def run_reference_audit(
        self,
        *,
        clip_id: str,
        person_reference_images: dict[str, Path],
    ) -> ReplacementAuditResult:
        del clip_id, person_reference_images
        self.reference_calls += 1
        return ReplacementAuditResult(status="passed", finding_type="ok", confidence=1.0)

    def run_render_audit(
        self,
        *,
        clip_id: str,
        rendered_output_path: Path,
        person_reference_images: dict[str, Path],
    ) -> ReplacementAuditResult:
        del clip_id, rendered_output_path, person_reference_images
        self.render_calls += 1
        if self.render_calls <= self.forced_render_failures:
            return ReplacementAuditResult(
                status="retry",
                finding_type="not_replaced",
                confidence=1.0,
            )
        return ReplacementAuditResult(status="passed", finding_type="ok", confidence=1.0)


def _resolve_clip_path() -> Path:
    override = os.environ.get("MULTIPERSON_CLIP_PATH")
    if override:
        return Path(override)
    preferred = REPO / "work" / "shots" / "smoke-multiperson.mp4"
    if preferred.exists():
        return preferred
    return REPO / "work" / "clips" / "smoke-live.mp4"


def _resolve_person_frame_paths() -> dict[str, Path]:
    defaults = {
        "actor_a": REPO / "work" / "keyframes" / "smoke-multiperson_actor_a.png",
        "actor_b": REPO / "work" / "keyframes" / "smoke-multiperson_actor_b.png",
    }
    fallback_frame = REPO / "work" / "frames" / "smoke-live.png"
    resolved: dict[str, Path] = {}
    for person_id, default_path in defaults.items():
        override = os.environ.get(f"MULTIPERSON_{person_id.upper()}_FRAME_PATH")
        if override:
            resolved[person_id] = Path(override)
            continue
        resolved[person_id] = default_path if default_path.exists() else fallback_frame
    return resolved


def _reset_outputs(paths: dict[str, Path]) -> None:
    for target_path in paths.values():
        if target_path.exists():
            target_path.unlink()


def _resolve_profile_dir() -> Path:
    override = os.environ.get("SMOKE_PROFILE_DIR")
    if override:
        return Path(override)
    preferred = REPO / "browser" / "edge-proxy-smoke-profile"
    if preferred.exists():
        return preferred
    return REPO / "work" / "tmp-proxy-launch-profile"


def _resolve_executable_path() -> Path | None:
    override = os.environ.get("BROWSER_EXECUTABLE")
    if override:
        return Path(override)
    if DEFAULT_EDGE_EXECUTABLE.exists():
        return DEFAULT_EDGE_EXECUTABLE
    return None


def main() -> int:
    clip_path = _resolve_clip_path()
    person_frame_paths = _resolve_person_frame_paths()
    paths = build_project_paths(REPO)
    state_path = REPO / "work" / "live_state" / f"{CLIP_ID}.json"
    output_path = REPO / "output" / "rendered" / f"{CLIP_ID}.mp4"
    notification_path = paths.logs_notifications_dir / f"{CLIP_ID}.json"
    person_output_paths = {
        person_id: REPO / "work" / "chatgpt_refs" / f"{CLIP_ID}_{person_id}.png"
        for person_id in person_frame_paths
    }
    reset_state = os.environ.get("RESET_STATE", "1") != "0"
    forced_render_failures = int(os.environ.get("FORCE_RENDER_AUDIT_FAILURES", "0"))

    if reset_state:
        _reset_outputs(
            {
                "state": state_path,
                "output": output_path,
                "notification": notification_path,
                **person_output_paths,
            }
        )

    missing_inputs = [path.as_posix() for path in [clip_path, *person_frame_paths.values()] if not path.exists()]
    if missing_inputs:
        print(
            {
                "status": "preflight_blocked",
                "missing_inputs": missing_inputs,
            },
            flush=True,
        )
        return 2

    request = LiveClipRequest(
        clip_id=CLIP_ID,
        clip_path=clip_path,
        frame_path=next(iter(person_frame_paths.values())),
        prompt=os.environ.get("MULTIPERSON_PROMPT", "replace actor_a with jett and actor_b with sage"),
        state_path=state_path,
        rendered_output_path=output_path,
        person_frame_paths=person_frame_paths,
        max_retry_attempts=3,
    )
    audit_runner = ForcedAuditRunner(forced_render_failures=forced_render_failures)

    try:
        with sync_playwright() as playwright:
            context = launch_persistent_context(
                playwright,
                PersistentContextRequest(
                    profile_dir=_resolve_profile_dir(),
                    downloads_dir=REPO / "work" / "downloads",
                    default_timeout_ms=20_000,
                    headless=os.environ.get("HEADLESS", "0") == "1",
                    executable_path=_resolve_executable_path(),
                    proxy_server=os.environ.get("PROXY_SERVER"),
                ),
            )
            try:
                result = run_single_clip_live_flow(
                    request=request,
                    chatgpt_page=context.new_page(),
                    runninghub_page=context.new_page(),
                    chatgpt_adapter=ChatGptPageAdapter(start_url=CHATGPT_URL),
                    runninghub_adapter=RunningHubPageAdapter(workflow_url=WORKFLOW_URL),
                    audit_runner=audit_runner,
                )
            finally:
                context.close()
    except Exception as exc:
        print(
            {
                "status": "preflight_blocked",
                "error": type(exc).__name__,
                "detail": str(exc),
                "clip_path": clip_path.as_posix(),
                "person_frame_paths": {
                    person_id: frame_path.as_posix()
                    for person_id, frame_path in person_frame_paths.items()
                },
            },
            flush=True,
        )
        return 2

    state = load_live_state(state_path) if state_path.exists() else None
    print(
        {
            "result": result,
            "clip_id": CLIP_ID,
            "clip_path": clip_path.as_posix(),
            "person_frame_paths": {
                person_id: frame_path.as_posix()
                for person_id, frame_path in person_frame_paths.items()
            },
            "forced_render_audit_failures": forced_render_failures,
            "state_step": None if state is None else state.step,
            "state_pause_reason": (
                None
                if state is None or state.pause_reason is None
                else state.pause_reason.value
            ),
            "state_task_id": None if state is None else state.runninghub_task_id,
            "person_reference_images": (
                {}
                if state is None
                else {
                    person_id: image_path.as_posix()
                    for person_id, image_path in state.person_reference_images.items()
                }
            ),
            "render_exists": output_path.exists(),
            "render_size": output_path.stat().st_size if output_path.exists() else 0,
            "notification_path": notification_path.as_posix(),
            "notification_exists": notification_path.exists(),
            "reference_audit_calls": audit_runner.reference_calls,
            "render_audit_calls": audit_runner.render_calls,
        },
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
