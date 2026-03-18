from dataclasses import dataclass
from pathlib import Path


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
