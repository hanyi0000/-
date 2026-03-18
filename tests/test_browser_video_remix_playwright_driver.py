from pathlib import Path

from scripts.browser_video_remix.playwright_driver import (
    BrowserLaunchRequest,
    PersistentContextRequest,
    build_browser_launch_options,
    build_persistent_context_options,
)


def test_build_browser_launch_options_uses_persistent_profile() -> None:
    request = BrowserLaunchRequest(
        profile_dir=Path("browser/profile"),
        headless=False,
    )

    options = build_browser_launch_options(request)

    assert options["user_data_dir"] == "browser/profile"
    assert options["headless"] is False


def test_build_persistent_context_options_sets_downloads_and_timeout() -> None:
    request = PersistentContextRequest(
        profile_dir=Path("browser/profile"),
        downloads_dir=Path("work/downloads"),
        default_timeout_ms=15000,
        headless=False,
    )

    options = build_persistent_context_options(request)

    assert options["user_data_dir"] == "browser/profile"
    assert options["downloads_path"] == "work/downloads"
    assert options["accept_downloads"] is True
    assert options["default_timeout_ms"] == 15000
