from pathlib import Path

from scripts.browser_video_remix.playwright_driver import (
    BrowserLaunchRequest,
    PersistentContextRequest,
    build_browser_launch_options,
    build_persistent_context_options,
    capture_page_snapshot,
    launch_persistent_context,
    resolve_browser_channel,
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


def test_resolve_browser_channel_prefers_msedge_when_present() -> None:
    channel = resolve_browser_channel(
        preferred_channel=None,
        edge_path_exists=True,
    )

    assert channel == "msedge"


def test_launch_persistent_context_passes_channel_and_timeout(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakeContext:
        def set_default_timeout(self, timeout_ms: int) -> None:
            captured["default_timeout_ms"] = timeout_ms

    class FakeChromium:
        def launch_persistent_context(self, user_data_dir: str, **kwargs: object) -> FakeContext:
            captured["user_data_dir"] = user_data_dir
            captured["kwargs"] = kwargs
            return FakeContext()

    class FakePlaywright:
        chromium = FakeChromium()

    context = launch_persistent_context(
        playwright=FakePlaywright(),
        request=PersistentContextRequest(
            profile_dir=tmp_path / "browser" / "profile",
            downloads_dir=tmp_path / "work" / "downloads",
            default_timeout_ms=15000,
            headless=False,
        ),
        edge_path_exists=True,
    )

    assert context is not None
    assert captured["user_data_dir"] == (tmp_path / "browser" / "profile").as_posix()
    assert captured["kwargs"]["channel"] == "msedge"
    assert captured["kwargs"]["accept_downloads"] is True
    assert captured["default_timeout_ms"] == 15000


def test_capture_page_snapshot_writes_html_and_screenshot(tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    screenshot_path = tmp_path / "artifacts" / "page.png"
    html_path = tmp_path / "artifacts" / "page.html"

    class FakePage:
        def goto(self, url: str, wait_until: str) -> None:
            captured["url"] = url
            captured["wait_until"] = wait_until

        def screenshot(self, path: str, full_page: bool) -> None:
            captured["screenshot_path"] = path
            captured["full_page"] = full_page
            Path(path).write_text("fake-image", encoding="utf-8")

        def content(self) -> str:
            return "<html>ok</html>"

    class FakeContext:
        def new_page(self) -> FakePage:
            return FakePage()

    capture_page_snapshot(
        context=FakeContext(),
        url="https://example.com/workflow",
        screenshot_path=screenshot_path,
        html_path=html_path,
    )

    assert captured["url"] == "https://example.com/workflow"
    assert captured["wait_until"] == "domcontentloaded"
    assert captured["full_page"] is True
    assert html_path.read_text(encoding="utf-8") == "<html>ok</html>"
