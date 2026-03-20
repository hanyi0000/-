import runpy
from pathlib import Path


SCRIPT_PATH = Path(r"D:/codex-worktrees/browser-video-remix-phase2/work/run_live_smoke_multiperson.py")


def test_resolve_proxy_server_defaults_to_legacy_smoke_proxy(monkeypatch) -> None:
    monkeypatch.delenv("PROXY_SERVER", raising=False)

    module = runpy.run_path(SCRIPT_PATH.as_posix(), run_name="smoke_helper_test")

    assert module["_resolve_proxy_server"]() == "socks5://127.0.0.1:1080"
