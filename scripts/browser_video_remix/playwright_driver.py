from dataclasses import dataclass
from pathlib import Path

EDGE_EXECUTABLE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


@dataclass(frozen=True)
class BrowserLaunchRequest:
    profile_dir: Path
    headless: bool


@dataclass(frozen=True)
class PersistentContextRequest:
    profile_dir: Path
    downloads_dir: Path
    default_timeout_ms: int
    headless: bool


def build_browser_launch_options(request: BrowserLaunchRequest) -> dict[str, str | bool]:
    return {
        "user_data_dir": request.profile_dir.as_posix(),
        "headless": request.headless,
    }


def build_persistent_context_options(
    request: PersistentContextRequest,
) -> dict[str, str | bool | int]:
    return {
        "user_data_dir": request.profile_dir.as_posix(),
        "downloads_path": request.downloads_dir.as_posix(),
        "accept_downloads": True,
        "default_timeout_ms": request.default_timeout_ms,
        "headless": request.headless,
    }


def resolve_browser_channel(
    preferred_channel: str | None,
    edge_path_exists: bool,
) -> str | None:
    if preferred_channel:
        return preferred_channel
    if edge_path_exists:
        return "msedge"
    return None


def launch_persistent_context(
    playwright: object,
    request: PersistentContextRequest,
    edge_path_exists: bool | None = None,
) -> object:
    request.profile_dir.mkdir(parents=True, exist_ok=True)
    request.downloads_dir.mkdir(parents=True, exist_ok=True)

    resolved_edge_exists = EDGE_EXECUTABLE.exists() if edge_path_exists is None else edge_path_exists
    channel = resolve_browser_channel(
        preferred_channel=None,
        edge_path_exists=resolved_edge_exists,
    )
    options = build_persistent_context_options(request)
    user_data_dir = str(options.pop("user_data_dir"))
    default_timeout_ms = int(options.pop("default_timeout_ms"))
    if channel is not None:
        options["channel"] = channel

    context = playwright.chromium.launch_persistent_context(
        user_data_dir,
        **options,
    )
    context.set_default_timeout(default_timeout_ms)
    return context


def capture_page_snapshot(
    context: object,
    url: str,
    screenshot_path: Path,
    html_path: Path,
) -> None:
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")
    page.screenshot(path=screenshot_path.as_posix(), full_page=True)
    html_path.write_text(page.content(), encoding="utf-8")
