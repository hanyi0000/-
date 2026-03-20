import runpy
import sys
import types
from pathlib import Path


SCRIPT_PATH = Path(r"D:/codex-worktrees/browser-video-remix-phase2/work/run_live_smoke_multiperson.py")


def test_resolve_proxy_server_defaults_to_legacy_smoke_proxy(monkeypatch) -> None:
    monkeypatch.delenv("PROXY_SERVER", raising=False)
    playwright_module = types.ModuleType("playwright")
    sync_api_module = types.ModuleType("playwright.sync_api")
    sync_api_module.sync_playwright = object()
    monkeypatch.setitem(sys.modules, "playwright", playwright_module)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_module)

    module = runpy.run_path(SCRIPT_PATH.as_posix(), run_name="smoke_helper_test")
    module["_resolve_proxy_server"].__globals__["_port_is_open"] = lambda host, port: port == 1080

    assert module["_resolve_proxy_server"]() == "socks5://127.0.0.1:1080"


def test_resolve_proxy_server_prefers_active_mixed_port_when_legacy_port_is_closed(
    monkeypatch,
) -> None:
    monkeypatch.delenv("PROXY_SERVER", raising=False)
    playwright_module = types.ModuleType("playwright")
    sync_api_module = types.ModuleType("playwright.sync_api")
    sync_api_module.sync_playwright = object()
    monkeypatch.setitem(sys.modules, "playwright", playwright_module)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_module)

    module = runpy.run_path(SCRIPT_PATH.as_posix(), run_name="smoke_helper_test")
    module["_resolve_proxy_server"].__globals__["_port_is_open"] = lambda host, port: port == 7890

    assert module["_resolve_proxy_server"]() == "socks5://127.0.0.1:7890"
