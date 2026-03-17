from pathlib import Path

from scripts.browser_video_remix.playwright_driver import (
    BrowserLaunchRequest,
    build_browser_launch_options,
)


def test_build_browser_launch_options_uses_persistent_profile() -> None:
    request = BrowserLaunchRequest(
        profile_dir=Path("browser/profile"),
        headless=False,
    )

    options = build_browser_launch_options(request)

    assert options["user_data_dir"] == "browser/profile"
    assert options["headless"] is False
