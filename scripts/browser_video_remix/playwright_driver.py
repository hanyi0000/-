from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrowserLaunchRequest:
    profile_dir: Path
    headless: bool


def build_browser_launch_options(request: BrowserLaunchRequest) -> dict[str, str | bool]:
    return {
        "user_data_dir": request.profile_dir.as_posix(),
        "headless": request.headless,
    }
